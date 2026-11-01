# 추천 오케스트레이션 테스트. 논문·LLM 응답은 모두 직접 만든 가짜이며 실제 논문이 아니다.
import asyncio
import json

import coach
import vision
from papers import Paper
from retrieval import Retriever
from test_insights import PUSH_HEAVY, D, T, W

CFG = vision.VisionConfig("key", "https://x.test/v1", "coach-model")
NOKEY = vision.VisionConfig("", "https://x.test/v1", "coach-model")


def paper(pmid, title, abstract, conclusion="", types=("Meta-Analysis",), emb=None):
    return Paper(pmid=pmid, title=title, abstract=abstract, conclusion=conclusion, journal="Test J", year=2020,
                 pub_types=list(types), authors="Doe J et al.", embedding=emb)


VOL = paper("101", "Weekly resistance training volume and muscle hypertrophy",
            "Weekly resistance training volume was related to muscle hypertrophy in a dose response manner.",
            "Higher weekly volume gave greater hypertrophy.")
REAR = paper("102", "Rear deltoid exercise electromyography",
             "Posterior deltoid activation was measured by electromyography during rear deltoid exercise variations.",
             "Reverse fly produced the highest activation.")
PP = paper("103", "Shoulder muscle imbalance between pulling and pushing in resistance training",
           "Scapular control and shoulder muscle imbalance were assessed in resistance training pulling pushing.")
CORPUS = [VOL, REAR, PP]


def run(c):
    return asyncio.run(c)


def raises(fn, exc):
    try:
        fn()
    except exc:
        return
    raise AssertionError("예외가 발생해야 합니다")


def findings_of(payload):
    return json.loads(payload["messages"][1]["content"].split("FINDINGS_JSON:\n", 1)[1])["findings"]


def fake_llm(mutate=None, status=200, raw=None):
    """각 발견 사항에 대해 '증거로 받은 첫 PMID' 를 인용하는 정상 응답을 만든다. mutate 로 변형 가능."""
    calls = []

    async def post(url, headers, payload):
        calls.append((url, headers, payload))
        if raw is not None:
            return status, raw
        recs = [{"insight_id": f["insight_id"], "summary": f"요약 {f['insight_id']}", "suggestion": "조정 제안",
                 "pmids": [f["evidence"][0]["pmid"]]} for f in findings_of(payload)]
        if mutate:
            recs = mutate(recs)
        return status, {"choices": [{"message": {"content": json.dumps({"recommendations": recs}, ensure_ascii=False)}}]}

    post.calls = calls
    return post


def rec(days=PUSH_HEAVY, post=None, cfg=CFG, corpus=CORPUS, **kw):
    post = post or fake_llm()
    out = run(coach.recommend(days, kw.pop("weight_kg", None), Retriever(corpus), cfg=cfg, post=post, **kw))
    return out, post


def by_id(out):
    return {i["id"]: i for i in out["insights"]}


def test_happy_path_retrieves_and_cites():
    out, post = rec()
    ins = by_id(out)
    assert [p["pmid"] for p in ins["push_pull"]["papers"]] == ["103"]
    assert ins["low_volume:shoulders_rear"]["papers"][0]["pmid"] == "102"
    adv = ins["low_volume:shoulders_rear"]["advice"]
    assert adv["pmids"] == ["102"] and adv["summary"].startswith("요약")
    assert out["generated"] and out["model"] == "coach-model" and out["llm_error"] is None and out["retrieval"] == "keyword"
    assert out["papers_in_db"] == 3 and out["disclaimer"] and len(post.calls) == 1  # LLM 은 한 번만 호출
    assert post.calls[0][0] == "https://x.test/v1/chat/completions"
    p = ins["low_volume:shoulders_rear"]["papers"][0]
    assert p["snippet"] == "Reverse fly produced the highest activation." and p["year"] == 2020 and p["journal"] == "Test J"


def test_user_note_text_is_never_sent_to_the_llm():
    secret = "비밀메모XYZ 어깨 통증 심함"
    days = PUSH_HEAVY + [D("2026-10-19", T(secret))]
    out, post = rec(days)
    assert "pain:shoulder" in by_id(out)                       # 통증은 분석에 반영되지만
    sent = json.dumps(post.calls[0][2], ensure_ascii=False)
    assert "비밀메모XYZ" not in sent and secret not in sent    # 메모 원문은 전송되지 않는다


def test_fabricated_or_unrelated_citations_are_dropped():
    def mutate(recs):
        recs[0]["pmids"] = ["999999"]                           # 존재하지 않는 PMID
        recs[1]["pmids"] = ["103" if recs[1]["insight_id"] != "push_pull" else "102"]  # 다른 발견 사항의 논문
        return recs
    out, _ = rec(post=fake_llm(mutate))
    first, second = out["insights"][0], out["insights"][1]
    assert first["advice"] is None and second["advice"] is None
    assert first["papers"] and second["papers"]                 # 논문 목록 자체는 그대로 보여준다


def test_citation_format_variants_are_normalized():
    def mutate(recs):
        recs[0]["pmids"] = [f"PMID: {recs[0]['pmids'][0]}", f"[{recs[0]['pmids'][0]}]", int(recs[0]["pmids"][0]), True, None, "x"]
        return recs
    out, _ = rec(post=fake_llm(mutate))
    assert out["insights"][0]["advice"]["pmids"] == [out["insights"][0]["papers"][0]["pmid"]]  # 중복 제거


def test_bad_llm_output_shapes_are_ignored():
    for raw in ("not json at all", json.dumps({"recommendations": "x"}), json.dumps({"foo": 1}),
                json.dumps({"recommendations": [None, 5, {"insight_id": 3}, {"insight_id": "nope", "pmids": ["101"], "summary": "s"}]}),
                json.dumps({"recommendations": [{"insight_id": "push_pull", "pmids": ["103"], "summary": ""}]})):
        out, _ = rec(post=fake_llm(raw={"choices": [{"message": {"content": raw}}]}))
        assert out["generated"] is False and all(i["advice"] is None for i in out["insights"]), raw
        assert any(i["papers"] for i in out["insights"])


def test_unparseable_llm_text_reports_error_but_keeps_results():
    out, _ = rec(post=fake_llm(raw={"choices": [{"message": {"content": "sorry"}}]}))
    assert out["llm_error"] and "논문 목록" in out["llm_error"] and out["insights"]


def test_llm_http_errors_degrade_gracefully():
    for status, key in ((429, "한도"), (402, "크레딧"), (401, "인증"), (500, "문제")):
        out, post = rec(post=fake_llm(status=status, raw={"detail": "x"}))
        assert out["generated"] is False and key in out["llm_error"] and out["insights"]
        assert len(post.calls) == 1


def test_llm_is_skipped_when_disabled_unconfigured_or_nothing_retrieved():
    out, post = rec(use_llm=False)
    assert post.calls == [] and out["llm_error"] is None and not out["generated"]
    out, post = rec(cfg=NOKEY)
    assert post.calls == [] and out["llm_error"] is None and out["insights"]
    out, post = rec(corpus=[])                                  # 논문 DB 가 비어 있음
    assert post.calls == [] and out["papers_in_db"] == 0 and out["insights"]
    assert all(i["papers"] == [] and i["advice"] is None for i in out["insights"])
    unrelated = [paper("1", "Cooking rice", "grain texture water")]
    out, post = rec(corpus=unrelated)                           # 관련 논문 없음 -> 억지로 인용하지 않는다
    assert post.calls == [] and all(i["papers"] == [] for i in out["insights"])


def test_no_insights_means_no_calls():
    out, post = rec(days=[])
    assert out["insights"] == [] and post.calls == [] and out["stats"]["days_with_data"] == 0


def test_hybrid_retrieval_uses_one_embedding_call():
    calls = []

    async def embed(queries):
        calls.append(list(queries))
        return [[1.0, 0.0] for _ in queries]

    out, _ = rec(embed=embed)
    assert out["retrieval"] == "hybrid" and len(calls) == 1
    assert len(calls[0]) == len(set(calls[0]))                  # 질의 중복 제거


def test_embedding_failures_fall_back_to_keyword_search():
    async def boom(queries):
        raise RuntimeError("embedding api down")

    async def wrong_count(queries):
        return [[1.0]]

    for embed in (boom, wrong_count):
        out, _ = rec(embed=embed)
        assert out["retrieval"] == "keyword" and by_id(out)["push_pull"]["papers"]


def test_validate_advice_limits():
    allowed = {"a": {"1", "2", "3", "4"}}
    ok = coach.validate_advice({"recommendations": [{"insight_id": "a", "summary": "x" * 999, "suggestion": "y" * 999,
                                                      "pmids": ["1", "2", "3", "4"]}]}, allowed)
    assert len(ok["a"]["summary"]) == 300 and len(ok["a"]["suggestion"]) == 300 and ok["a"]["pmids"] == ["1", "2", "3"]
    dup = coach.validate_advice({"recommendations": [{"insight_id": "a", "summary": "first", "pmids": ["1"]},
                                                      {"insight_id": "a", "summary": "second", "pmids": ["2"]}]}, allowed)
    assert dup["a"]["summary"] == "first"
    assert coach.validate_advice(None, allowed) == {} and coach.validate_advice([], allowed) == {}


def test_excerpt_prefers_conclusion_and_truncates_cleanly():
    p = paper("1", "t", "word " * 300, conclusion="Conclusion text.")
    assert coach._excerpt(p, 400) == "Conclusion text."
    long = paper("2", "t", "alpha beta gamma delta " * 100)
    ex = coach._excerpt(long, 50)
    assert ex.startswith("…") and len(ex) <= 50 and not ex[1:].startswith(" ")
    assert coach._excerpt(paper("3", "t", "short abstract"), 400) == "short abstract"
    longc = paper("4", "t", "x", conclusion="word " * 200)
    assert coach._excerpt(longc, 50).endswith("…") and len(coach._excerpt(longc, 50)) <= 50


# ---- 관련성 필터 (Phase 4.5) -----------------------------------------------------------

def test_evidence_includes_titles():
    _, post = rec()
    titles = [e["title"] for f in findings_of(post.calls[0][2]) for e in f["evidence"]]
    assert titles and all(titles) and "Rear deltoid exercise electromyography" in titles


def test_papers_marked_irrelevant_by_llm_are_hidden_and_not_cited():
    off = paper("104", "Rear deltoid activation electromyography in clinic",
                "Posterior deltoid exercise electromyography activation in a clinical sample.")

    def mutate(recs):
        for r in recs:
            if r["insight_id"] == "low_volume:shoulders_rear":
                r["irrelevant_pmids"] = ["102", "555"]  # 555 는 증거 목록에 없으므로 무시된다
        return recs

    out, _ = rec(post=fake_llm(mutate), corpus=CORPUS + [off])
    ins = by_id(out)["low_volume:shoulders_rear"]
    shown = [p["pmid"] for p in ins["papers"]]
    assert "102" not in shown and "104" in shown and ins["hidden_papers"] == 1
    assert ins["advice"] is None or "102" not in ins["advice"]["pmids"]
    assert "hidden_papers" not in by_id(out)["push_pull"]       # 표시 안 한 발견 사항은 그대로


def test_irrelevant_everything_drops_advice_but_not_the_response():
    def mutate(recs):
        for r in recs:
            r["irrelevant_pmids"] = list(r["pmids"])
        return recs

    out, _ = rec(post=fake_llm(mutate))
    assert all(i["advice"] is None for i in out["insights"]) and out["generated"] is False


def test_missing_irrelevant_field_keeps_all_papers():
    out, _ = rec()                                              # fake_llm 기본 응답에는 irrelevant_pmids 가 없다
    assert by_id(out)["push_pull"]["papers"] and "hidden_papers" not in by_id(out)["push_pull"]


def test_parse_irrelevant_only_accepts_known_pmids():
    allowed = {"a": {"1", "2"}}
    parsed = {"recommendations": [{"insight_id": "a", "irrelevant_pmids": ["PMID: 1", 9, "x", True]},
                                  {"insight_id": "zzz", "irrelevant_pmids": ["1"]}]}
    assert coach.parse_irrelevant(parsed, allowed) == {"a": {"1"}}
    assert coach.parse_irrelevant(None, allowed) == {} and coach.parse_irrelevant({"recommendations": 3}, allowed) == {}

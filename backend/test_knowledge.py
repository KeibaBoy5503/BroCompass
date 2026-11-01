# topics / papers / pubmed / embeddings / ingest 테스트. pytest 없이도 돌아가도록 일반 assert 만 사용한다.
# 아래 XML 은 파서 검증용으로 직접 만든 '가짜' 데이터이며 실제 논문이 아니다.
import json
import os
import tempfile

import embeddings
import ingest_pubmed
import pubmed
from papers import Paper, PaperStore
from topics import TOPICS, pubmed_query, queries_for

DOCTYPE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2019//EN" '
    '"https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_190101.dtd">\n'
)

ART_1001 = """
<PubmedArticle><MedlineCitation Status="MEDLINE" Owner="NLM"><PMID Version="1">1001</PMID>
<Article PubModel="Print"><Journal><JournalIssue CitedMedium="Print"><Volume>1</Volume>
<PubDate><Year>2019</Year><Month>Jan</Month></PubDate></JournalIssue><Title>Test Journal of Synthetic Data</Title>
<ISOAbbreviation>Test J Synth</ISOAbbreviation></Journal>
<ArticleTitle>Effect of <i>synthetic</i> training on   test outcomes.</ArticleTitle>
<Abstract><AbstractText Label="BACKGROUND" NlmCategory="BACKGROUND">Background text.</AbstractText>
<AbstractText Label="CONCLUSIONS" NlmCategory="CONCLUSIONS">Conclusion with H<sub>2</sub>O and CO2.</AbstractText></Abstract>
<AuthorList><Author><LastName>Doe</LastName><Initials>J</Initials></Author>
<Author><LastName>Roe</LastName><Initials>R</Initials></Author></AuthorList>
<PublicationTypeList><PublicationType UI="D000">Meta-Analysis</PublicationType>
<PublicationType UI="D001">Systematic Review</PublicationType></PublicationTypeList></Article></MedlineCitation>
<PubmedData><ArticleIdList><ArticleId IdType="pubmed">1001</ArticleId><ArticleId IdType="doi">10.0000/test.1</ArticleId>
</ArticleIdList></PubmedData></PubmedArticle>"""

ART_1002 = """
<PubmedArticle><MedlineCitation><PMID>1002</PMID><Article><Journal><JournalIssue>
<PubDate><MedlineDate>2018 Jan-Feb</MedlineDate></PubDate></JournalIssue><ISOAbbreviation>Iso Abbr</ISOAbbreviation></Journal>
<ArticleTitle>Unstructured abstract paper</ArticleTitle>
<Abstract><AbstractText>Plain abstract without labels.</AbstractText></Abstract>
<AuthorList><Author><CollectiveName>Synthetic Study Group</CollectiveName></Author></AuthorList>
</Article></MedlineCitation><PubmedData/></PubmedArticle>"""

ART_1003_NO_ABSTRACT = """
<PubmedArticle><MedlineCitation><PMID>1003</PMID><Article><Journal><Title>J</Title></Journal>
<ArticleTitle>No abstract here</ArticleTitle></Article></MedlineCitation></PubmedArticle>"""


def xml_of(*articles):
    return DOCTYPE + "<PubmedArticleSet>" + "".join(articles) + "</PubmedArticleSet>"


def raises(fn, exc=ValueError):
    try:
        fn()
    except exc:
        return
    raise AssertionError("예외가 발생해야 합니다")


def tmp_store():
    return PaperStore(os.path.join(tempfile.mkdtemp(), "p.db"))


# --- topics ---
def test_topics_are_consistent():
    assert {"volume", "rear_delt", "push_pull", "protein", "plateau", "shoulder_pain", "combat"} <= set(TOPICS)
    for t in TOPICS.values():
        assert t.queries and all(q.isascii() for q in t.queries)  # 논문 초록이 영어이므로 질의도 영어
        q = pubmed_query(t)
        assert q.startswith("(") and "hasabstract[text]" in q
    assert queries_for("volume", "volume") == list(TOPICS["volume"].queries)  # 중복 제거


# --- pubmed URL / 파싱 ---
def test_urls():
    u = pubmed.esearch_url('("a b"[tiab]) AND c', 30)
    assert u.startswith("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?")
    assert "retmode=json" in u and "sort=relevance" in u and "retmax=30" in u and "tool=BroCompass" in u
    assert " " not in u and "api_key" not in u and "email" not in u
    u = pubmed.efetch_url(["1", "2", "3"], api_key="K", email="a@b.c")
    assert "id=1,2,3" in u and "retmode=xml" in u and "rettype" not in u and "api_key=K" in u and "email=a%40b.c" in u


def test_parse_esearch():
    assert pubmed.parse_esearch(json.dumps({"esearchresult": {"idlist": ["1", "22", "x", 5]}})) == ["1", "22"]
    assert pubmed.parse_esearch(json.dumps({"esearchresult": {}})) == []
    raises(lambda: pubmed.parse_esearch(json.dumps({"esearchresult": {"ERROR": "bad query"}})))
    raises(lambda: pubmed.parse_esearch("<html>"))
    raises(lambda: pubmed.parse_esearch(json.dumps({"header": {}})))


def test_parse_efetch_full_record():
    papers = {p.pmid: p for p in pubmed.parse_efetch(xml_of(ART_1001, ART_1002, ART_1003_NO_ABSTRACT))}
    assert set(papers) == {"1001", "1002"}  # 초록 없는 1003 은 제외
    p = papers["1001"]
    assert p.title == "Effect of synthetic training on test outcomes."  # 인라인 태그·중복 공백 정리
    assert p.abstract == "BACKGROUND: Background text. CONCLUSIONS: Conclusion with H2O and CO2."  # 원문 라벨 보존
    assert p.conclusion == "Conclusion with H2O and CO2."
    assert p.journal == "Test Journal of Synthetic Data" and p.year == 2019
    assert p.doi == "10.0000/test.1" and p.pub_types == ["Meta-Analysis", "Systematic Review"]
    assert p.authors == "Doe J et al."
    q = papers["1002"]
    assert q.year == 2018 and q.journal == "Iso Abbr" and q.conclusion == "" and q.doi == ""
    assert q.abstract == "Plain abstract without labels." and q.authors == "Synthetic Study Group"


def test_parse_efetch_dedupes_and_rejects_bad_xml():
    assert len(pubmed.parse_efetch(xml_of(ART_1001, ART_1001))) == 1
    assert pubmed.parse_efetch(xml_of()) == []
    raises(lambda: pubmed.parse_efetch("<PubmedArticleSet><oops>"))
    evil = '<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><PubmedArticleSet>&a;</PubmedArticleSet>'
    raises(lambda: pubmed.parse_efetch(evil))


# --- papers 저장소 ---
def paper(pmid="1", abstract="abs", **kw):
    return Paper(pmid=pmid, title=f"t{pmid}", abstract=abstract, pub_types=["Meta-Analysis"], **kw)


def test_store_roundtrip_and_version():
    s = tmp_store()
    assert s.count() == 0 and s.version() == (0, 0, 0) and s.all() == []
    s.upsert([paper("1", conclusion="c", year=2020, journal="J", doi="d", authors="A B")], now=100)
    s.upsert([paper("2")], now=200)
    got = {p.pmid: p for p in s.all()}
    assert s.count() == 2 and s.version() == (2, 200, 0)
    assert got["1"].conclusion == "c" and got["1"].year == 2020 and got["1"].pub_types == ["Meta-Analysis"]


def test_store_keeps_embedding_only_if_abstract_unchanged():
    s = tmp_store()
    s.upsert([paper("1", "same"), paper("2", "old")])
    assert {p.pmid for p in s.missing_embeddings()} == {"1", "2"} and s.embed_model() is None
    s.set_embeddings({"1": [1.0, 0.0], "2": [0.0, 1.0]}, "m")
    assert s.missing_embeddings() == [] and s.embed_model() == "m" and s.version()[2] == 2
    s.upsert([paper("1", "same"), paper("2", "NEW abstract")])
    assert [p.pmid for p in s.missing_embeddings()] == ["2"]  # 바뀐 논문만 다시 임베딩
    assert {p.pmid: p.embedding for p in s.all()}["1"] == [1.0, 0.0]


# --- embeddings ---
def test_embed_config_and_request():
    assert not embeddings.EmbedConfig.from_env({"NVIDIA_API_KEY": "k"}).enabled  # 모델 미지정 -> 꺼짐
    c = embeddings.EmbedConfig.from_env({"NVIDIA_API_KEY": "k", "EMBED_MODEL": "m"})
    assert c.enabled and c.base_url.endswith("nvidia.com/v1")
    p = embeddings.build_request(c, ["x" * 5000], "query")
    assert p["input_type"] == "query" and len(p["input"][0]) == embeddings.MAX_PASSAGE_CHARS
    oa = embeddings.EmbedConfig.from_env({"EMBED_API_KEY": "k", "EMBED_MODEL": "m", "EMBED_BASE_URL": "https://api.openai.com/v1"})
    assert "input_type" not in embeddings.build_request(oa, ["a"], "query")  # OpenAI 는 모르는 필드 거부
    raises(lambda: embeddings.EmbedConfig.from_env({"EMBED_BASE_URL": "http://evil.example"}))


def test_parse_embedding_response():
    body = {"data": [{"index": 1, "embedding": [0, 2]}, {"index": 0, "embedding": [3, 4]}]}
    v = embeddings.parse_response(body, 2)
    assert v[0] == [0.6, 0.8] and v[1] == [0.0, 1.0]  # index 순 정렬 + 단위벡터
    for bad in ({"data": []}, {"x": 1}, {"data": [{"embedding": [1, 2]}, {"embedding": [1]}]},
                {"data": [{"embedding": [float("nan"), 1]}, {"embedding": [1, 1]}]}, None):
        raises(lambda b=bad: embeddings.parse_response(b, 2))


# --- ingest ---
def fake_get_factory(ids_by_topic_marker, fail_marker=None):
    calls = []

    def get(url):
        calls.append(url)
        if "esearch" in url:
            if fail_marker and fail_marker in url:
                raise RuntimeError("네트워크 오류")
            for marker, ids in ids_by_topic_marker.items():
                if marker in url:
                    return json.dumps({"esearchresult": {"idlist": ids}})
            return json.dumps({"esearchresult": {"idlist": []}})
        ids = url.split("id=")[1].split("&")[0].split(",")
        return xml_of(*[ART_1001.replace("1001", i).replace("10.0000/test.1", f"10.0/{i}") for i in ids])

    get.calls = calls
    return get


def test_ingest_dedupes_across_topics_and_isolates_failures():
    s = tmp_store()
    get = fake_get_factory({"hypertrophy": ["1", "2"], "protein": ["2", "3"], "overload": ["9"]}, fail_marker="overload")
    logs = []
    out = ingest_pubmed.ingest(s, ["volume", "protein", "plateau"], 30, get=get, sleep=lambda: None, log=logs.append)
    assert out == {"volume": 2, "protein": 1, "plateau": 0}  # protein 은 이미 받은 2 를 제외
    assert {p.pmid for p in s.all()} == {"1", "2", "3"}  # 한 토픽이 실패해도 나머지는 저장됨
    assert any("실패" in l for l in logs)
    efetches = [u for u in get.calls if "efetch" in u]
    assert len(efetches) == 2 and all("retmode=xml" in u for u in efetches)


def test_ingest_batches_large_id_lists():
    s = tmp_store()
    ids = [str(i) for i in range(1, 251)]
    get = fake_get_factory({"hypertrophy": ids})
    ingest_pubmed.ingest(s, ["volume"], 250, get=get, sleep=lambda: None, log=lambda m: None)
    assert s.count() == 250 and len([u for u in get.calls if "efetch" in u]) == 3  # 100 + 100 + 50


def test_embed_missing_with_fake_api():
    s = tmp_store()
    s.upsert([paper(str(i)) for i in range(1, 6)])
    cfg = embeddings.EmbedConfig("k", "https://x.test/v1", "m")
    seen = []

    def post(url, headers, payload):
        seen.append((url, payload["input_type"] if "input_type" in payload else None))
        return 200, {"data": [{"index": i, "embedding": [1.0, float(i)]} for i in range(len(payload["input"]))]}

    n = ingest_pubmed.embed_missing(s, cfg, post, log=lambda m: None, batch=2, pause=0)
    assert n == 5 and s.missing_embeddings() == [] and s.embed_model() == "m"
    assert len(seen) == 3 and seen[0][0] == "https://x.test/v1/embeddings"


def test_embed_missing_stops_on_http_error():
    s = tmp_store()
    s.upsert([paper("1"), paper("2")])
    cfg = embeddings.EmbedConfig("k", "https://x.test/v1", "m")
    n = ingest_pubmed.embed_missing(s, cfg, lambda *a: (404, {}), log=lambda m: None, pause=0)
    assert n == 0 and len(s.missing_embeddings()) == 2

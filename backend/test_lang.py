# 서버가 만드는 문장의 언어(ko/ja/en) 테스트.
import json

import coach
import vision
from insights import analyze, classify
from test_coach import PUSH_HEAVY, fake_llm, rec
from test_insights import D, S, W, get, ids
from texts import LANGS, norm_lang, tx

KANA = "ぁあ-んァ-ヶ"


def has_kana(s):
    return any("぀" <= c <= "ヿ" for c in s)


def has_hangul(s):
    return any("가" <= c <= "힣" for c in s)


def test_norm_lang():
    assert [norm_lang(x) for x in ("ja", "en", "ko", "fr", None, 3, "")] == ["ja", "en", "ko", "ko", "ko", "ko", "ko"]
    assert LANGS == ("ko", "ja", "en")


def test_insights_same_ids_in_every_language():
    base = ids(analyze(PUSH_HEAVY, 75, "ko"))
    assert base
    for lang in ("ja", "en"):
        assert ids(analyze(PUSH_HEAVY, 75, lang)) == base


def test_insight_text_is_translated_without_leftover_korean():
    ja, en = analyze(PUSH_HEAVY, 75, "ja"), analyze(PUSH_HEAVY, 75, "en")
    for a, check in ((ja, has_kana), (en, lambda s: s.isascii() or True)):
        for i in a.insights:
            assert not has_hangul(i["title"] + i["detail"]), i["id"]
            for sb in i["suggested_blocks"]:
                assert not has_hangul(sb["title"]), sb
    assert "プル" in get(ja, "push_pull")["title"] or "プル" in get(ja, "push_pull")["detail"]
    assert "pull" in get(en, "push_pull")["title"].lower()
    for a in (ja, en):
        for i in a.insights:
            assert i["title"] and i["detail"] and "{" not in i["title"] + i["detail"]


def test_numbers_are_identical_across_languages():
    k = get(analyze(PUSH_HEAVY, 75, "ko"), "push_pull")["detail"]
    e = get(analyze(PUSH_HEAVY, 75, "en"), "push_pull")["detail"]
    j = get(analyze(PUSH_HEAVY, 75, "ja"), "push_pull")["detail"]
    nums = lambda s: [t for t in __import__("re").findall(r"\d+(?:\.\d+)?", s)]
    assert nums(k) == nums(e) == nums(j)


def test_suggested_names_classify_to_the_same_muscle_in_every_language():
    for lang in ("ko", "ja", "en"):
        a = analyze(PUSH_HEAVY, 75, lang)
        for i in a.insights:
            for sb in i["suggested_blocks"]:
                muscle = i["id"].split(":")[-1] if i["id"].startswith("low_volume:") else "back"
                assert classify(sb["title"]) is not None, (lang, sb["title"])
                if i["id"].startswith("low_volume:"):
                    assert classify(sb["title"]) == muscle, (lang, i["id"], sb["title"])


def test_session_texts_and_unknown_lang_falls_back_to_korean():
    days = [D("2026-10-21", S("스파링", 60, 6)), D("2026-10-28", S("스파링", 60, 8), S("복싱", 30, 8))]
    assert "格闘技" in get(analyze(days, None, "ja"), "combat")["title"]
    assert "combat sports" in get(analyze(days, None, "en"), "combat")["title"]
    assert "2.0x" in get(analyze(days, None, "en"), "load_spike")["detail"]
    assert analyze(days, None, "fr").insights[0]["title"] == analyze(days, None, "ko").insights[0]["title"]


def test_hints_and_empty_state_translated():
    assert analyze([], None, "ja").stats["hints"] == [tx("ja", "no_data")]
    a = analyze([D("2026-10-27", W("벤치프레스", 1, 5, 60))], None, "en")
    assert any("Fewer than" in h for h in a.stats["hints"]) and any("weight" in h for h in a.stats["hints"])


def test_vision_prompt_and_warnings_follow_language():
    assert "Japanese" in vision.prompt_with_hint("", "ja") and "{language}" not in vision.prompt_with_hint("", "ja")
    assert "English" in vision.prompt_with_hint("", "en")
    assert vision.prompt_with_hint("", "ko") == vision.PROMPT and "Korean" in vision.PROMPT
    assert vision.prompt_with_hint("", "xx") == vision.PROMPT
    text = json.dumps({"items": [{"name": "Salad", "kcal": 150, "protein_g": 20, "carb_g": 40, "fat_g": 8,
                                  "confidence": "low"}], "note": "ok"})
    _, _, ko = vision.parse_meal(text)
    _, _, en = vision.parse_meal(text, "en")
    _, _, ja = vision.parse_meal(text, "ja")
    assert len(ko) == len(en) == len(ja) == 2
    assert "do not match" in en[0] and "確認" in ja[0] and "맞지" in ko[0]


def test_coach_prompt_language_and_disclaimer():
    assert "Write in Japanese." in coach.system_prompt("ja") and "Write in English." in coach.system_prompt("en")
    assert "Write in Korean." in coach.SYSTEM_PROMPT.replace("{language}", "Korean")
    assert "{language}" not in coach.system_prompt("xx") and "Korean" in coach.system_prompt("xx")
    # JSON 스키마의 중괄호가 깨지지 않는다
    assert '{"recommendations"' in coach.system_prompt("ja")
    out, post = rec(post=fake_llm(), lang="ja")
    sent = post.calls[0][2]["messages"][0]["content"]
    assert "Write in Japanese." in sent
    assert has_kana(out["disclaimer"]) and not has_hangul(out["disclaimer"])
    assert all(not has_hangul(i["title"]) for i in out["insights"])
    out_ko, _ = rec(post=fake_llm())
    assert out_ko["disclaimer"] == coach.DISCLAIMER and has_hangul(out_ko["disclaimer"])

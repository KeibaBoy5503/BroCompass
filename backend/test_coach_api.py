# FastAPI 가 설치된 환경에서 실행하는 HTTP 수준 테스트 (pytest + httpx 필요).
from fastapi.testclient import TestClient

import main
import vision
from papers import PaperStore
from test_coach import CORPUS, fake_llm
from test_insights import PUSH_HEAVY


def client(monkeypatch, tmp_path, corpus=CORPUS, rpm=100, post=None):
    store = PaperStore(str(tmp_path / "p.db"))
    store.upsert(corpus)
    monkeypatch.setattr(main, "paper_store", store)
    monkeypatch.setitem(main._retriever_cache, "version", None)  # 색인 캐시 초기화
    monkeypatch.setattr(main, "coach_cfg", vision.VisionConfig("k", "https://x.test/v1", "m"))
    monkeypatch.setattr(main, "coach_limiter", vision.RateLimiter(rpm))
    monkeypatch.setattr(main, "_http_post", post or fake_llm())
    return TestClient(main.app)


def test_stats(monkeypatch, tmp_path):
    r = client(monkeypatch, tmp_path).get("/api/papers/stats").json()
    assert r["count"] == 3 and r["llm_configured"] is True and r["embeddings_enabled"] is False


def test_recommend_ok(monkeypatch, tmp_path):
    r = client(monkeypatch, tmp_path).post("/api/coach/recommend", json={"days": PUSH_HEAVY, "use_llm": True})
    body = r.json()
    assert r.status_code == 200 and body["generated"] and body["papers_in_db"] == 3
    assert any(i["advice"] for i in body["insights"])


def test_recommend_works_without_papers_and_llm_failure(monkeypatch, tmp_path):
    c = client(monkeypatch, tmp_path, corpus=[])
    assert c.post("/api/coach/recommend", json={"days": PUSH_HEAVY}).json()["insights"]
    bad = fake_llm(status=429, raw={"detail": "x"})
    c = client(monkeypatch, tmp_path, post=bad)
    body = c.post("/api/coach/recommend", json={"days": PUSH_HEAVY}).json()
    assert body["llm_error"] and body["insights"]


def test_validation(monkeypatch, tmp_path):
    c = client(monkeypatch, tmp_path)
    day = {"date": "2026-10-19", "blocks": []}
    assert c.post("/api/coach/recommend", json={"days": [day] * 29}).status_code == 422
    assert c.post("/api/coach/recommend", json={"days": [], "weight_kg": 10}).status_code == 422
    assert c.post("/api/coach/recommend", json={"days": [{"date": "2026-13-45", "blocks": []}]}).status_code == 422
    assert c.post("/api/coach/recommend", json={"days": [{"date": "2026-10-19", "blocks": [{}] * 201}]}).status_code == 422


def test_rate_limit(monkeypatch, tmp_path):
    c = client(monkeypatch, tmp_path, rpm=1)
    assert c.post("/api/coach/recommend", json={"days": []}).status_code == 200
    r = c.post("/api/coach/recommend", json={"days": []})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1


def test_recommend_lang_validation_and_effect(monkeypatch, tmp_path):
    c = client(monkeypatch, tmp_path)
    assert c.post("/api/coach/recommend", json={"days": PUSH_HEAVY, "lang": "fr"}).status_code == 422
    body = c.post("/api/coach/recommend", json={"days": PUSH_HEAVY, "lang": "en"}).json()
    assert "pulling" in " ".join(i["title"].lower() for i in body["insights"])
    ko = c.post("/api/coach/recommend", json={"days": PUSH_HEAVY}).json()  # lang 생략 = 한국어
    assert any("당기기" in i["title"] for i in ko["insights"])


def test_daily_cap_counts_only_llm_calls(monkeypatch, tmp_path):
    from ratelimit import DailyCap

    c = client(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "ai_daily_cap", DailyCap(1))
    assert c.post("/api/coach/recommend", json={"days": PUSH_HEAVY, "use_llm": False}).status_code == 200
    assert c.post("/api/coach/recommend", json={"days": PUSH_HEAVY, "use_llm": False}).status_code == 200
    assert c.post("/api/coach/recommend", json={"days": PUSH_HEAVY, "use_llm": True}).status_code == 200
    assert c.post("/api/coach/recommend", json={"days": PUSH_HEAVY, "use_llm": True}).status_code == 429

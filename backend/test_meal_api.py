import base64
import json

from fastapi.testclient import TestClient

import main
import vision

JPEG_B64 = base64.b64encode(b"\xff\xd8\xff\xe0" + b"\x00" * 50).decode()
GOOD = {"items": [{"name": "닭가슴살", "kcal": 220, "protein_g": 42, "carb_g": 0, "fat_g": 5}], "note": "추정"}


def setup(monkeypatch, post, key="k", rpm=100):
    monkeypatch.setattr(main, "vision_cfg", vision.VisionConfig(key, "https://x.test/v1", "m"))
    monkeypatch.setattr(main, "vision_limiter", vision.RateLimiter(rpm))
    monkeypatch.setattr(main, "_http_post", post)
    return TestClient(main.app)


async def good_post(url, headers, payload):
    return 200, {"choices": [{"message": {"content": json.dumps(GOOD, ensure_ascii=False)}}]}


def test_analyze_ok(monkeypatch):
    c = setup(monkeypatch, good_post)
    r = c.post("/api/meal/analyze", json={"image": JPEG_B64, "mime": "image/jpeg"})
    assert r.status_code == 200
    assert r.json()["items"][0]["name"] == "닭가슴살" and r.json()["model"] == "m"


def test_no_key_503(monkeypatch):
    c = setup(monkeypatch, good_post, key="")
    assert c.post("/api/meal/analyze", json={"image": JPEG_B64}).status_code == 503


def test_bad_image_422(monkeypatch):
    c = setup(monkeypatch, good_post)
    assert c.post("/api/meal/analyze", json={"image": "zzz"}).status_code == 422
    assert c.post("/api/meal/analyze", json={"image": JPEG_B64, "mime": "image/gif"}).status_code == 422


def test_rate_limited_429_with_retry_after(monkeypatch):
    c = setup(monkeypatch, good_post, rpm=1)
    assert c.post("/api/meal/analyze", json={"image": JPEG_B64}).status_code == 200
    r = c.post("/api/meal/analyze", json={"image": JPEG_B64})
    assert r.status_code == 429 and int(r.headers["Retry-After"]) >= 1


def test_upstream_error_does_not_leak_key(monkeypatch):
    async def bad(url, headers, payload):
        return 401, {"detail": "invalid key nvapi-SECRET"}

    c = setup(monkeypatch, bad, key="nvapi-SECRET")
    r = c.post("/api/meal/analyze", json={"image": JPEG_B64})
    assert r.status_code == 502 and "nvapi-SECRET" not in r.text


def test_hint_is_forwarded_and_new_fields_are_returned(monkeypatch):
    seen = {}

    async def post(url, headers, payload):
        seen["text"] = payload["messages"][0]["content"][0]["text"]
        body = {"items": [{"name": "닭가슴살", "grams": 150, "kcal": 220, "protein_g": 42, "carb_g": 0, "fat_g": 5,
                           "confidence": "medium"}], "note": ""}
        return 200, {"choices": [{"message": {"content": json.dumps(body, ensure_ascii=False)}}]}

    c = setup(monkeypatch, post)
    r = c.post("/api/meal/analyze", json={"image": JPEG_B64, "hint": "닭가슴살 샐러드"})
    item = r.json()["items"][0]
    assert r.status_code == 200 and "닭가슴살 샐러드" in seen["text"]
    assert item["grams"] == 150 and item["confidence"] == "medium" and item["macro_kcal"] == 213


def test_hint_too_long_is_rejected(monkeypatch):
    c = setup(monkeypatch, good_post)
    assert c.post("/api/meal/analyze", json={"image": JPEG_B64, "hint": "x" * 101}).status_code == 422


def test_meal_lang_validation_and_prompt(monkeypatch):
    seen = {}

    async def spy(url, headers, payload):
        seen["prompt"] = payload["messages"][0]["content"][0]["text"]
        return await good_post(url, headers, payload)

    c = setup(monkeypatch, spy)
    body = {"image": JPEG_B64, "mime": "image/jpeg"}
    assert c.post("/api/meal/analyze", json={**body, "lang": "zz"}).status_code == 422
    assert c.post("/api/meal/analyze", json={**body, "lang": "ja"}).status_code == 200
    assert "Japanese" in seen["prompt"]
    assert c.post("/api/meal/analyze", json=body).status_code == 200 and "Korean" in seen["prompt"]


def test_per_ip_limit_and_daily_cap(monkeypatch):
    from ratelimit import DailyCap, KeyedRateLimiter

    c = setup(monkeypatch, good_post)
    payload = {"image": JPEG_B64, "mime": "image/jpeg"}
    monkeypatch.setattr(main, "ip_vision_limiter", KeyedRateLimiter(1))
    assert c.post("/api/meal/analyze", json=payload).status_code == 200
    assert c.post("/api/meal/analyze", json=payload).status_code == 429  # 같은 IP 두 번째
    monkeypatch.setattr(main, "ip_vision_limiter", KeyedRateLimiter(0))
    monkeypatch.setattr(main, "ai_daily_cap", DailyCap(1))
    assert c.post("/api/meal/analyze", json=payload).status_code == 200
    r = c.post("/api/meal/analyze", json=payload)
    assert r.status_code == 429 and "오늘" in r.json()["detail"]

import pytest
from fastapi.testclient import TestClient

from store import NoteStore


@pytest.fixture
def store(tmp_path):
    return NoteStore(str(tmp_path / "t.db"))


def test_get_missing(store):
    assert store.get("2026-10-19") is None


def test_put_then_get_korean(store):
    blocks = [{"id": "a", "kind": "text", "title": "어깨 컨디션 안 좋음"}]
    won = store.put("2026-10-19", blocks, 100)
    assert won["updated_at"] == 100
    assert store.get("2026-10-19")["blocks"] == blocks


def test_newer_wins_older_ignored(store):
    store.put("2026-10-19", [{"id": "new"}], 200)
    won = store.put("2026-10-19", [{"id": "old"}], 100)  # 오래된 요청
    assert won["updated_at"] == 200 and won["blocks"] == [{"id": "new"}]
    assert store.get("2026-10-19")["blocks"] == [{"id": "new"}]


def test_equal_timestamp_keeps_existing(store):
    store.put("2026-10-19", [{"id": "first"}], 100)
    won = store.put("2026-10-19", [{"id": "second"}], 100)
    assert won["blocks"] == [{"id": "first"}]


def test_list_dates_skips_empty_and_out_of_range(store):
    store.put("2026-10-17", [{"id": "x"}], 1)
    store.put("2026-10-18", [], 2)  # 비어 있으면 제외
    store.put("2026-10-19", [{"id": "y"}], 3)
    store.put("2026-11-01", [{"id": "z"}], 4)
    assert store.list_dates("2026-10-01", "2026-10-31") == ["2026-10-17", "2026-10-19"]


def test_api_roundtrip(tmp_path, monkeypatch):
    import main

    monkeypatch.setattr(main, "store", NoteStore(str(tmp_path / "api.db")))
    c = TestClient(main.app)
    assert c.get("/api/notes/2026-10-19").status_code == 404
    r = c.put("/api/notes/2026-10-19", json={"blocks": [{"id": "a"}], "updated_at": 5})
    assert r.status_code == 200 and r.json()["updated_at"] == 5
    r = c.put("/api/notes/2026-10-19", json={"blocks": [], "updated_at": 1})
    assert r.json()["blocks"] == [{"id": "a"}]
    assert c.get("/api/notes", params={"start": "2026-10-01", "end": "2026-10-31"}).json() == {
        "dates": ["2026-10-19"]
    }


@pytest.mark.parametrize("bad", ["2026-13-01", "20261019", "2026-10-1", "abc"])
def test_api_rejects_bad_date(bad):
    import main

    assert TestClient(main.app).get(f"/api/notes/{bad}").status_code == 422


# ---- 공개 배포용: 사용자 분리 / 제한 (HTTP 수준) ----

import main  # noqa: E402
from ratelimit import DailyCap, KeyedRateLimiter  # noqa: E402

CID_A = "a" * 20
CID_B = "b" * 20


def _client(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "store", NoteStore(str(tmp_path / "api.db")))
    return TestClient(main.app)


def test_api_notes_are_separated_by_client_id(monkeypatch, tmp_path):
    c = _client(monkeypatch, tmp_path)
    body = {"blocks": [{"id": "x"}], "updated_at": 5}
    assert c.put("/api/notes/2026-11-01", json=body, headers={"X-Client-Id": CID_A}).status_code == 200
    assert c.get("/api/notes/2026-11-01", headers={"X-Client-Id": CID_A}).status_code == 200
    assert c.get("/api/notes/2026-11-01", headers={"X-Client-Id": CID_B}).status_code == 404


def test_api_bad_client_id_is_400_and_required_when_enabled(monkeypatch, tmp_path):
    c = _client(monkeypatch, tmp_path)
    assert c.get("/api/notes/2026-11-01", headers={"X-Client-Id": "short"}).status_code == 400
    monkeypatch.setattr(main, "REQUIRE_CLIENT_ID", True)
    assert c.get("/api/notes/2026-11-01").status_code == 400


def test_api_per_ip_note_limit_and_quota(monkeypatch, tmp_path):
    c = _client(monkeypatch, tmp_path)
    monkeypatch.setattr(main, "ip_notes_limiter", KeyedRateLimiter(1))
    body = {"blocks": [], "updated_at": 1}
    assert c.put("/api/notes/2026-11-01", json=body).status_code == 200
    r = c.put("/api/notes/2026-11-02", json=body)
    assert r.status_code == 429 and "Retry-After" in r.headers
    monkeypatch.setattr(main, "ip_notes_limiter", KeyedRateLimiter(0))
    monkeypatch.setattr(main, "store", NoteStore(str(tmp_path / "q.db"), max_notes_per_owner=1))
    assert c.put("/api/notes/2026-11-01", json=body).status_code == 200
    assert c.put("/api/notes/2026-11-02", json=body).status_code == 413

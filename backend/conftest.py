"""테스트가 서로 IP 한도·하루 총량을 공유하지 않도록 매 테스트마다 넉넉한 값으로 초기화한다.
(fastapi 가 없는 환경에서는 main 을 불러오지 못하므로 조용히 건너뛴다.)"""
import pytest


@pytest.fixture(autouse=True)
def _reset_public_limits(monkeypatch):
    try:
        import main
        from ratelimit import DailyCap, KeyedRateLimiter
    except ImportError:
        yield
        return
    monkeypatch.setattr(main, "ip_vision_limiter", KeyedRateLimiter(10_000))
    monkeypatch.setattr(main, "ip_coach_limiter", KeyedRateLimiter(10_000))
    monkeypatch.setattr(main, "ip_notes_limiter", KeyedRateLimiter(10_000))
    monkeypatch.setattr(main, "ai_daily_cap", DailyCap(0))
    monkeypatch.setattr(main, "REQUIRE_CLIENT_ID", False)
    yield

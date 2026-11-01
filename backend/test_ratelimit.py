from ratelimit import DailyCap, KeyedRateLimiter, client_ip


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_keys_are_independent():
    c = Clock()
    rl = KeyedRateLimiter(2, 60, c)
    assert rl.allow("a") and rl.allow("a") and not rl.allow("a")
    assert rl.allow("b")  # 다른 IP 는 영향 없음


def test_window_slides_and_retry_after():
    c = Clock()
    rl = KeyedRateLimiter(1, 60, c)
    assert rl.allow("a") and not rl.allow("a")
    c.t = 20
    assert rl.retry_after("a") == 40
    c.t = 60
    assert rl.allow("a")


def test_disabled_when_limit_zero():
    rl = KeyedRateLimiter(0)
    assert all(rl.allow("a") for _ in range(100))


def test_max_keys_sweeps_stale_then_rejects_new():
    c = Clock()
    rl = KeyedRateLimiter(5, 60, c, max_keys=2)
    assert rl.allow("a") and rl.allow("b")
    assert not rl.allow("c")  # 가득 참, 아직 만료 전
    c.t = 61
    assert rl.allow("c")  # 만료된 키를 정리한 뒤 허용


def test_daily_cap_resets_next_day():
    day = ["2026-11-01"]
    cap = DailyCap(2, lambda: day[0])
    assert cap.allow() and cap.allow() and not cap.allow()
    day[0] = "2026-11-02"
    assert cap.allow()
    assert all(DailyCap(0).allow() for _ in range(5))


def test_client_ip_proxy_trust():
    h = {"x-forwarded-for": "203.0.113.9, 10.0.0.1"}
    assert client_ip(h, "10.0.0.1", True) == "203.0.113.9"
    assert client_ip(h, "10.0.0.1", False) == "10.0.0.1"  # 위조 방지: 신뢰하지 않으면 무시
    assert client_ip({"x-forwarded-for": "not-an-ip"}, "10.0.0.1", True) == "10.0.0.1"
    assert client_ip({}, "", True) == "unknown"

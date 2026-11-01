"""공개 배포용 요청 제한 (표준 라이브러리만 사용).

- KeyedRateLimiter: 키(보통 IP)별 슬라이딩 윈도우. 한 사람이 무료 API 한도를 독점하지 못하게 한다.
- DailyCap: 하루 총량 제한. 서버 전체의 AI 호출 수를 막아 키의 한도 소진을 방지한다.
- client_ip: 요청에서 접속자 IP 를 꺼낸다. 프록시 뒤에서는 X-Forwarded-For 의 첫 값을 쓴다.

상태는 프로세스 메모리에만 있다. 서버를 여러 대로 늘리거나 재시작하면 초기화되므로
'데모를 보호하는 안전장치'이지 정식 요금/보안 시스템이 아니다.
"""
import ipaddress
import math
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Mapping, Optional


class KeyedRateLimiter:
    def __init__(
        self,
        limit: int,
        window: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ):
        self.limit, self.window, self._clock, self.max_keys = limit, window, clock, max_keys
        self._hits: dict[str, deque[float]] = {}

    def _prune(self, q: deque[float], now: float) -> None:
        while q and now - q[0] >= self.window:
            q.popleft()

    def _sweep(self, now: float) -> None:
        for k in [k for k, q in self._hits.items() if not q or now - q[-1] >= self.window]:
            del self._hits[k]

    def allow(self, key: str) -> bool:
        """limit <= 0 이면 제한하지 않는다."""
        if self.limit <= 0:
            return True
        now = self._clock()
        q = self._hits.get(key)
        if q is None:
            if len(self._hits) >= self.max_keys:
                self._sweep(now)
                if len(self._hits) >= self.max_keys:  # 메모리 보호: 새 키는 거절
                    return False
            q = self._hits[key] = deque()
        self._prune(q, now)
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True

    def retry_after(self, key: str) -> int:
        q = self._hits.get(key)
        if not q:
            return 1
        now = self._clock()
        self._prune(q, now)
        return max(1, math.ceil(self.window - (now - q[0]))) if q else 1


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class DailyCap:
    """UTC 기준 하루 총 호출 수 제한. limit <= 0 이면 제한하지 않는다."""

    def __init__(self, limit: int, today: Callable[[], str] = _utc_day):
        self.limit, self._today = limit, today
        self._day, self._count = today(), 0

    def allow(self) -> bool:
        if self.limit <= 0:
            return True
        day = self._today()
        if day != self._day:
            self._day, self._count = day, 0
        if self._count >= self.limit:
            return False
        self._count += 1
        return True


def _valid_ip(s: str) -> Optional[str]:
    try:
        return str(ipaddress.ip_address(s.strip()))
    except ValueError:
        return None


def client_ip(headers: Mapping[str, str], peer: str, trust_proxy: bool) -> str:
    """접속자 IP. trust_proxy=False 면 직접 연결 상대(peer)만 신뢰한다.

    trust_proxy=True 는 '신뢰하는 프록시가 X-Forwarded-For 를 덮어써 주는' 환경에서만 켠다.
    그렇지 않은 곳에서 켜면 접속자가 헤더를 위조해 제한을 피할 수 있다.
    """
    if trust_proxy:
        xff = headers.get("x-forwarded-for", "")
        first = _valid_ip(xff.split(",")[0]) if xff else None
        if first:
            return first
    return peer or "unknown"

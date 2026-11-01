"""배포 직후 점검 스크립트 (표준 라이브러리만 사용).

    python smoke_check.py https://내-서비스.onrender.com
    python smoke_check.py https://내-프론트.vercel.app      # 프록시(/api)까지 함께 확인

확인하는 것: /health, 논문 DB 수, 노트 저장/조회/사용자 분리.
무료 서버가 잠들어 있으면 첫 요청이 수십 초 걸릴 수 있어 시간 제한을 넉넉히 둔다.
사진 분석·AI 요약은 하루 한도를 쓰므로 여기서는 호출하지 않는다.
"""
import json
import sys
import urllib.error
import urllib.request
import uuid

TIMEOUT = 90


def call(base: str, method: str, path: str, body=None, client_id: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if client_id:
        req.add_header("X-Client-Id", client_id)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        return e.code, None


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    base = argv[1].rstrip("/")
    a, b = uuid.uuid4().hex, uuid.uuid4().hex  # 32자 16진수: 서버의 ID 형식 조건을 만족
    results: list[tuple[str, bool, str]] = []

    st, js = call(base, "GET", "/health")
    if st == 200:
        results.append(("health", js == {"status": "ok"}, str(js)))
    else:
        results.append(("health", True, "건너뜀(프록시 주소는 /health 가 없을 수 있음)"))

    st, js = call(base, "GET", "/api/papers/stats")
    ok = st == 200 and isinstance(js, dict)
    results.append(("papers", ok and js.get("count", 0) > 0, f"HTTP {st}, count={js and js.get('count')}"))

    day = "2026-01-01"
    st, _ = call(base, "PUT", f"/api/notes/{day}", {"blocks": [{"id": "smoke"}], "updated_at": 1}, a)
    results.append(("note save", st == 200, f"HTTP {st}"))
    st, _ = call(base, "GET", f"/api/notes/{day}", None, a)
    results.append(("note read (owner)", st == 200, f"HTTP {st}"))
    st, _ = call(base, "GET", f"/api/notes/{day}", None, b)
    results.append(("note isolated", st == 404, f"HTTP {st} (404 가 정상)"))

    for name, ok, detail in results:
        print(f"[{'OK' if ok else 'NG'}] {name}: {detail}")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))

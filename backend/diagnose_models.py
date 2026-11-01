"""AI 모델 점검 도구 (표준 라이브러리만 사용). 키는 환경변수에서 읽고 화면에 출력하지 않는다.

    python diagnose_models.py                       # 내 키로 쓸 수 있는 모델 목록(이미지 후보 표시)
    python diagnose_models.py --vision 모델ID,모델ID   # 작은 이미지를 실제로 보내 비전 모델이 되는지 시험
    python diagnose_models.py --text 모델ID,모델ID     # 텍스트 모델(코치 요약용)의 응답 시간 시험
    python diagnose_models.py --scan                # 내 키의 모든 모델을 동시에 시험해 '지금 되는' 텍스트 모델 찾기
    (--nothink: 추론 모델의 '생각' 기능을 끄는 옵션을 함께 보내 본다. 모델에 따라 무시될 수 있다)

무료 호스팅 모델은 예고 없이 종료되거나 계정에 따라 접근이 막힐 수 있다. 되는 모델을 찾으면
환경변수 VISION_MODEL / COACH_MODEL 에 넣어 서버를 다시 켠다.
"""
import argparse
import base64
import concurrent.futures
import json
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib

from vision import VisionConfig

VISION_HINTS = ("vision", "vlm", "-vl", "vl-", "paligemma", "pixtral", "llava", "gemma-3", "phi-3.5-vision",
                "phi-4-multimodal", "cosmos", "multimodal", "nemotron-nano-12b", "qwen")
DEFAULT_VISION = [
    "google/gemma-3-4b-it",
    "nvidia/nemotron-3.5-super-vl-120b-a12b",
    "microsoft/phi-3-vision-128k-instruct",
    "meta/llama-3.2-90b-vision-instruct",
    "nvidia/cosmos-reason2-8b",
]
DEFAULT_TEXT = ["openai/gpt-oss-20b"]


def make_png(size: int = 64) -> bytes:
    """단색 PNG (표준 라이브러리로 생성). 너무 작은 이미지를 거부하는 모델이 있어 64px 로 만든다."""
    row = b"\x00" + bytes([200, 60, 60]) * size
    raw = zlib.compress(row * size)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


TIMEOUT = 60.0  # --timeout 으로 바꿀 수 있다


def request(cfg: VisionConfig, method: str, path: str, body=None, timeout: float | None = None):
    timeout = timeout or TIMEOUT
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(cfg.base_url + path, data=data, method=method)
    req.add_header("Authorization", f"Bearer {cfg.api_key}")
    req.add_header("Content-Type", "application/json")
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read() or b"null"), time.monotonic() - t0
    except urllib.error.HTTPError as e:
        try:
            payload = json.loads(e.read() or b"null")
        except ValueError:
            payload = None
        return e.code, payload, time.monotonic() - t0
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, str(e), time.monotonic() - t0


def describe(js) -> str:
    """응답이 비어 있을 때 원인을 알 수 있게 구조를 요약한다 (본문 전체는 출력하지 않는다)."""
    try:
        ch = js["choices"][0]
        msg = ch["message"]
        content = msg.get("content")
        extra = {k: len(v) for k, v in msg.items() if k != "content" and isinstance(v, str)}
        usage = (js.get("usage") or {}).get("completion_tokens")
        return (f"content={'있음' if content else '비어있음'}, finish={ch.get('finish_reason')}, "
                f"다른 글 필드={extra or '없음'}, 생성 토큰={usage}")
    except (KeyError, IndexError, TypeError, AttributeError):
        return "구조 해석 실패: " + short(js)


def short(payload) -> str:
    return json.dumps(payload, ensure_ascii=False)[:240] if payload is not None else ""


def list_models(cfg: VisionConfig) -> int:
    st, js, _ = request(cfg, "GET", "/models")
    if st != 200 or not isinstance(js, dict):
        print(f"모델 목록을 가져오지 못했습니다 (HTTP {st}) {short(js)}")
        return 1
    ids = sorted(m.get("id", "") for m in js.get("data", []))
    cand = [i for i in ids if any(h in i.lower() for h in VISION_HINTS)]
    print(f"내 키로 보이는 모델 {len(ids)}개. 이미지 입력 후보(이름 기준 추정, 실제 지원은 --vision 으로 시험):")
    for i in cand:
        print("  ", i)
    for name in (cfg.model, "openai/gpt-oss-20b"):
        print(f"{'있음' if name in ids else '없음'}: {name}")
    return 0


def try_vision(cfg: VisionConfig, model: str, nothink: bool = False) -> bool:
    print(f"... {model} 시험 중 (최대 {TIMEOUT:.0f}초)", flush=True)
    b64 = base64.b64encode(make_png()).decode()
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "What color is this image? Answer in one word."},
            {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        ]}],
        "max_tokens": 1500,
    }
    if nothink:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    st, js, sec = request(cfg, "POST", "/chat/completions", payload)
    ok = st == 200
    answer = ""
    if ok:
        try:
            answer = (js["choices"][0]["message"].get("content") or "").strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            answer = ""
        if not answer:
            ok, answer = False, "내용이 비어 있어요 → " + describe(js)
        else:
            answer = f"{answer[:80]}  ({describe(js)})"
    print(f"[{'OK' if ok else 'NG'}] {model}  HTTP {st}  {sec:.1f}초  {answer if st == 200 else short(js)}", flush=True)
    return ok


def try_text(cfg: VisionConfig, model: str, nothink: bool = False) -> bool:
    print(f"... {model} 시험 중 (최대 {TIMEOUT:.0f}초)", flush=True)
    payload = {"model": model, "messages": [{"role": "user", "content": "Reply with the single word OK."}], "max_tokens": 400}
    if nothink:
        payload["chat_template_kwargs"] = {"enable_thinking": False}
    st, js, sec = request(cfg, "POST", "/chat/completions", payload)
    ok = st == 200
    answer = ""
    if ok:
        try:
            answer = (js["choices"][0]["message"].get("content") or "").strip()
        except (KeyError, IndexError, TypeError, AttributeError):
            answer = ""
        if not answer:
            ok, answer = False, "내용이 비어 있어요 → " + describe(js)
        else:
            answer = f"{answer[:80]}  ({describe(js)})"
    print(f"[{'OK' if ok else 'NG'}] {model}  HTTP {st}  {sec:.1f}초  {answer if st == 200 else short(js)}")
    return ok


SKIP_WORDS = ("embed", "rerank", "guard", "safety", "reward", "parse", "clip", "retriever", "nemoretriever",
              "vlm-embed", "riva", "tts", "asr", "image", "diffusion", "flux", "stable", "sdxl", "cosmos-predict")


def scan(cfg: VisionConfig, workers: int = 8) -> int:
    st, js, _ = request(cfg, "GET", "/models")
    if st != 200 or not isinstance(js, dict):
        print(f"모델 목록을 가져오지 못했습니다 (HTTP {st}) {short(js)}")
        return 1
    ids = sorted(m.get("id", "") for m in js.get("data", []))
    ids = [i for i in ids if i and not any(w in i.lower() for w in SKIP_WORDS)]
    print(f"{len(ids)}개 모델에 짧은 질문을 동시에 보냅니다 (모델당 최대 {TIMEOUT:.0f}초). 잠시만 기다리세요...\n", flush=True)

    def one(model: str):
        payload = {"model": model, "messages": [{"role": "user", "content": "Reply with the single word OK."}], "max_tokens": 400}
        st, js, sec = request(cfg, "POST", "/chat/completions", payload)
        text = ""
        if st == 200:
            try:
                text = (js["choices"][0]["message"].get("content") or "").strip()
            except (KeyError, IndexError, TypeError, AttributeError):
                text = ""
        return model, st, sec, text

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(one, ids))
    good = sorted((r for r in results if r[1] == 200 and r[3]), key=lambda r: r[2])
    empty = [r for r in results if r[1] == 200 and not r[3]]
    print(f"[응답 OK, 빠른 순] {len(good)}개")
    for m, _, sec, text in good:
        print(f"  {sec:5.1f}초  {m}  → {text[:30]}")
    if empty:
        print(f"\n[200 이지만 내용 비어 있음(추론 모델 가능성)] {len(empty)}개: " + ", ".join(r[0] for r in empty))
    slow = [r[0] for r in results if r[1] == 0]
    print(f"\n[시간 초과] {len(slow)}개, [404 등 오류] {sum(1 for r in results if r[1] not in (0, 200))}개")
    return 0 if good else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vision", nargs="?", const=",".join(DEFAULT_VISION), help="쉼표로 구분한 비전 모델 ID (비우면 기본 후보)")
    ap.add_argument("--text", nargs="?", const=",".join(DEFAULT_TEXT), help="쉼표로 구분한 텍스트 모델 ID")
    ap.add_argument("--scan", action="store_true", help="내 키의 모든 텍스트 모델을 동시에 시험")
    ap.add_argument("--nothink", action="store_true", help="추론 끄기 옵션(chat_template_kwargs)을 함께 보낸다")
    ap.add_argument("--timeout", type=float, default=60.0, help="모델 하나당 기다릴 최대 시간(초, 기본 60)")
    args = ap.parse_args()
    global TIMEOUT
    TIMEOUT = args.timeout
    cfg = VisionConfig.from_env()
    if not cfg.api_key:
        print("NVIDIA_API_KEY 환경변수가 없습니다. 이 터미널에서 먼저 설정하세요(키를 채팅에 붙여 넣지 마세요).")
        return 2
    print(f"서버 주소: {cfg.base_url}\n")
    if args.scan:
        return scan(cfg)
    if not args.vision and not args.text:
        return list_models(cfg)
    results = []
    for m in [x.strip() for x in (args.vision or "").split(",") if x.strip()]:
        results.append(try_vision(cfg, m, args.nothink))
    for m in [x.strip() for x in (args.text or "").split(",") if x.strip()]:
        results.append(try_text(cfg, m, args.nothink))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())

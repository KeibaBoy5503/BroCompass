"""BroCompass FastAPI 서버 (Phase 1: 계산기 API, Phase 2: 데일리 노트 저장)."""
import os
import re
from datetime import date as date_cls
from typing import Any, Literal, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

import calc
import coach
import embeddings
import vision
from papers import PaperStore
from retrieval import DEFAULT_MIN_COVERAGE, DEFAULT_MIN_REL_SCORE, Retriever
from ratelimit import DailyCap, KeyedRateLimiter, client_ip
from store import NoteQuotaError, NoteStore

def _cors_origins() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "http://localhost:3000")
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


app = FastAPI(title="BroCompass API", version="0.5.0")

# ---- 공개 배포 설정 (모두 환경변수, backend/.env.example 참고) ---------------------
# CORS_ORIGINS : 브라우저가 서버를 직접 호출할 때 허용할 주소(쉼표 구분). 프록시(/api rewrite) 구조면 기본값으로 충분.
# TRUST_PROXY=1: 신뢰하는 프록시가 X-Forwarded-For 를 붙여 주는 환경(Render 등)에서만 켠다.
# REQUIRE_CLIENT_ID=1: 공개 배포에서 켠다. 노트 API 가 X-Client-Id 없는 요청을 거절한다.
# IP_*_RPM / AI_DAILY_CAP: IP 별 분당 한도, 하루 AI 호출 총량 (0 이면 끔).
TRUST_PROXY = os.environ.get("TRUST_PROXY", "") == "1"
REQUIRE_CLIENT_ID = os.environ.get("REQUIRE_CLIENT_ID", "") == "1"
CLIENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{16,64}$")
ip_vision_limiter = KeyedRateLimiter(int(os.environ.get("IP_VISION_RPM", "6")))
ip_coach_limiter = KeyedRateLimiter(int(os.environ.get("IP_COACH_RPM", "4")))
ip_notes_limiter = KeyedRateLimiter(int(os.environ.get("IP_NOTES_RPM", "120")))
ai_daily_cap = DailyCap(int(os.environ.get("AI_DAILY_CAP", "300")))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

store = NoteStore(
    os.environ.get(
        "BROCOMPASS_DB", os.path.join(os.path.dirname(__file__), "brocompass.db")
    )
)


class CalcRequest(BaseModel):
    sex: Literal["male", "female"]
    age: int = Field(ge=10, le=100)
    height_cm: float = Field(ge=100, le=250)
    weight_kg: float = Field(ge=30, le=300)
    activity: Literal["sedentary", "light", "moderate", "active", "very_active"]
    goal: Literal["cut", "maintain", "bulk"]
    body_type: Literal["ectomorph", "mesomorph", "endomorph"] = "mesomorph"
    body_fat_pct: Optional[float] = Field(default=None, ge=3, le=60)


class CalcResponse(BaseModel):
    bmr: float
    tdee: float
    target_kcal: float
    carb_g: float
    protein_g: float
    fat_g: float


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/calc", response_model=CalcResponse)
async def calculate(req: CalcRequest):
    result = calc.calculate(**req.model_dump())
    return CalcResponse(**result.__dict__)


# ---- 데일리 노트 -----------------------------------------------------------
# 로그인은 없다. 대신 브라우저가 만든 무작위 ID(X-Client-Id)로 사용자별 노트를 분리한다.
# ID 를 아는 사람만 그 노트를 읽을 수 있는 '비밀 링크' 수준의 분리이며, 정식 인증이 아니다.
# 공개 배포에서는 REQUIRE_CLIENT_ID=1 로 켠다.


def _ip(request: Request) -> str:
    return client_ip(request.headers, request.client.host if request.client else "", TRUST_PROXY)


def owner_id(x_client_id: Optional[str] = Header(default=None)) -> str:
    if x_client_id is None:
        if REQUIRE_CLIENT_ID:
            raise HTTPException(status_code=400, detail="X-Client-Id 헤더가 필요합니다.")
        return ""
    if not CLIENT_ID_RE.match(x_client_id):
        raise HTTPException(status_code=400, detail="X-Client-Id 형식이 올바르지 않습니다.")
    return x_client_id


def _check_daily_cap() -> None:
    if not ai_daily_cap.allow():
        raise HTTPException(
            status_code=429,
            detail="오늘 AI 사용량 한도에 도달했어요. 내일 다시 시도해 주세요.",
            headers={"Retry-After": "3600"},
        )


def _limit_ip(request: Request, limiter: KeyedRateLimiter, detail: str) -> None:
    ip = _ip(request)
    if not limiter.allow(ip):
        raise HTTPException(
            status_code=429, detail=detail, headers={"Retry-After": str(limiter.retry_after(ip))}
        )


def _valid_date(d: str) -> str:
    # fromisoformat 은 "20261019" 같은 변형도 받으므로 형식을 함께 확인한다.
    try:
        if len(d) != 10 or date_cls.fromisoformat(d).isoformat() != d:
            raise ValueError
    except ValueError:
        raise HTTPException(status_code=422, detail="날짜는 YYYY-MM-DD 형식이어야 합니다.")
    return d


class NoteIn(BaseModel):
    blocks: list[dict[str, Any]] = Field(max_length=200)
    updated_at: int = Field(ge=0, description="클라이언트 수정 시각(ms)")


class NoteOut(BaseModel):
    date: str
    blocks: list[dict[str, Any]]
    updated_at: int


class DatesOut(BaseModel):
    dates: list[str]


@app.get("/api/notes/{date}", response_model=NoteOut)
def get_note(date: str, owner: str = Depends(owner_id)):
    note = store.get(_valid_date(date), owner)
    if note is None:
        raise HTTPException(status_code=404, detail="해당 날짜의 노트가 없습니다.")
    return note


@app.put("/api/notes/{date}", response_model=NoteOut)
def put_note(date: str, body: NoteIn, request: Request, owner: str = Depends(owner_id)):
    """서버에 더 최신 노트가 있으면 저장하지 않고 그 노트를 돌려준다 (클라이언트가 채택)."""
    _limit_ip(request, ip_notes_limiter, "저장 요청이 너무 많아요. 잠시 후 다시 시도해 주세요.")
    try:
        return store.put(_valid_date(date), body.blocks, body.updated_at, owner)
    except NoteQuotaError:
        raise HTTPException(status_code=413, detail="저장할 수 있는 노트 수를 넘었어요.")


@app.get("/api/notes", response_model=DatesOut)
def list_notes(start: str = Query(...), end: str = Query(...), owner: str = Depends(owner_id)):
    return {"dates": store.list_dates(_valid_date(start), _valid_date(end), owner)}


# ---- 식단 사진 분석 ---------------------------------------------------------
# 설정은 환경변수로 한다 (backend/.env.example 참고). API 키는 서버에만 있고 브라우저로 나가지 않는다.
# 주의: 로그인이 없으므로 서버 주소를 아는 누구나 호출할 수 있다. 그래서 IP 별 한도와 하루 총량(AI_DAILY_CAP)을 둔다.

vision_cfg = vision.VisionConfig.from_env()
vision_limiter = vision.RateLimiter(int(os.environ.get("VISION_RPM", "30")))


async def _http_post(url: str, headers: dict[str, str], payload: dict[str, Any]):
    import httpx  # 사진 분석을 쓸 때만 필요하므로 지연 import

    # 느린 무료 모델이 많아 기본 90초. 부족하면 AI_TIMEOUT_S 로 늘린다 (프론트 프록시 대기시간과 함께 고려).
    timeout_s = float(os.environ.get("AI_TIMEOUT_S", "90"))
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout_s, connect=10.0)) as client:
        try:
            r = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            raise vision.VisionError(504, "AI 분석 시간이 초과됐어요. 다시 시도해 주세요.")
        except httpx.HTTPError:
            raise vision.VisionError(502, "AI 서버에 연결하지 못했어요.")
    try:
        body: Any = r.json()
    except ValueError:
        body = r.text
    return r.status_code, body


class MealAnalyzeIn(BaseModel):
    image: str = Field(min_length=1, max_length=6_000_000, description="base64 (data: 접두사 없이)")
    mime: Literal["image/jpeg", "image/png", "image/webp"] = "image/jpeg"
    hint: str = Field(default="", max_length=100, description="음식 이름 힌트 (선택)")
    lang: str = Field(default="ko", pattern="^(ko|ja|en)$", description="결과 문장의 언어")


class MealItemOut(BaseModel):
    name: str
    kcal: float
    protein_g: float
    carb_g: float
    fat_g: float
    grams: Optional[float] = None
    confidence: Optional[Literal["high", "medium", "low"]] = None
    macro_kcal: Optional[float] = None


class MealAnalyzeOut(BaseModel):
    items: list[MealItemOut]
    note: str
    warnings: list[str]
    model: str


@app.post("/api/meal/analyze", response_model=MealAnalyzeOut)
async def analyze_meal(req: MealAnalyzeIn, request: Request):
    _limit_ip(request, ip_vision_limiter, "사진 분석 요청이 너무 많아요. 잠시 후 다시 시도해 주세요.")
    if not vision_limiter.allow():
        raise HTTPException(
            status_code=429,
            detail="사진 분석 요청이 너무 많아요. 잠시 후 다시 시도해 주세요.",
            headers={"Retry-After": str(vision_limiter.retry_after())},
        )
    _check_daily_cap()
    try:
        return await vision.analyze(req.image, req.mime, vision_cfg, _http_post, req.hint, req.lang)
    except vision.VisionError as e:
        raise HTTPException(status_code=e.status, detail=e.message)


# ---- 논문 기반 추천 (RAG) ----------------------------------------------------
# 논문 DB 는 ingest_pubmed.py 로 채운다. 설정은 backend/.env.example 참고.
# 주의: 로그인이 없다. IP 별 한도와 하루 총량으로 보호한다.

_vbase = vision_cfg
coach_cfg = vision.VisionConfig(
    _vbase.api_key, _vbase.base_url, (os.environ.get("COACH_MODEL") or "").strip() or "openai/gpt-oss-20b"
)
embed_cfg = embeddings.EmbedConfig.from_env()
paper_store = PaperStore(
    os.environ.get("BROCOMPASS_PAPERS_DB", os.path.join(os.path.dirname(__file__), "papers.db"))
)
coach_limiter = vision.RateLimiter(int(os.environ.get("COACH_RPM", "10")))
coach_min_coverage = float(os.environ.get("COACH_MIN_COVERAGE", DEFAULT_MIN_COVERAGE))
coach_min_rel = float(os.environ.get("COACH_MIN_REL", DEFAULT_MIN_REL_SCORE))  # 0 = 사용 안 함

_retriever_cache: dict[str, Any] = {"version": None, "retriever": None, "embed_ok": False}


def _get_retriever() -> tuple[Retriever, bool]:
    """논문 DB 가 바뀌었을 때만 색인을 다시 만든다. 저장된 임베딩이 현재 설정의 모델과 같을 때만 임베딩을 쓴다."""
    version = paper_store.version()
    if _retriever_cache["version"] != version:
        _retriever_cache["retriever"] = Retriever(paper_store.all())
        _retriever_cache["embed_ok"] = bool(
            embed_cfg.enabled and version[2] > 0 and paper_store.embed_model() == embed_cfg.model
        )
        _retriever_cache["version"] = version
    return _retriever_cache["retriever"], _retriever_cache["embed_ok"]


async def _embed_queries(queries: list[str]) -> list[list[float]]:
    status, body = await _http_post(
        f"{embed_cfg.base_url}/embeddings",
        {"Authorization": f"Bearer {embed_cfg.api_key}", "Content-Type": "application/json"},
        embeddings.build_request(embed_cfg, queries, "query"),
    )
    if status != 200:
        raise RuntimeError(f"embedding HTTP {status}")
    return embeddings.parse_response(body, len(queries))


class CoachDayIn(BaseModel):
    date: str
    blocks: list[dict[str, Any]] = Field(max_length=200)


class CoachIn(BaseModel):
    days: list[CoachDayIn] = Field(max_length=28)
    weight_kg: Optional[float] = Field(default=None, ge=30, le=300)
    use_llm: bool = True
    lang: str = Field(default="ko", pattern="^(ko|ja|en)$", description="결과 문장의 언어")


@app.get("/api/papers/stats")
def papers_stats():
    count, last, embedded = paper_store.version()
    return {
        "count": count,
        "last_fetched": last or None,  # epoch 초
        "embedded": embedded,
        "llm_configured": bool(coach_cfg.api_key),
        "embeddings_enabled": embed_cfg.enabled,
    }


@app.post("/api/coach/recommend")
async def coach_recommend(req: CoachIn, request: Request):
    for d in req.days:
        _valid_date(d.date)
    _limit_ip(request, ip_coach_limiter, "추천 요청이 너무 많아요. 잠시 후 다시 시도해 주세요.")
    if not coach_limiter.allow():
        raise HTTPException(
            status_code=429,
            detail="추천 요청이 너무 많아요. 잠시 후 다시 시도해 주세요.",
            headers={"Retry-After": str(coach_limiter.retry_after())},
        )
    if req.use_llm and coach_cfg.api_key:
        _check_daily_cap()  # 외부 AI 를 실제로 부르는 요청만 하루 총량에 센다
    retriever, embed_ok = await run_in_threadpool(_get_retriever)
    return await coach.recommend(
        [d.model_dump() for d in req.days],
        req.weight_kg,
        retriever,
        cfg=coach_cfg,
        post=_http_post,
        embed=_embed_queries if embed_ok else None,
        use_llm=req.use_llm,
        min_coverage=coach_min_coverage,
        min_rel_score=coach_min_rel,
        lang=req.lang,
    )

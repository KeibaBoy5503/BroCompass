"""임베딩 API(OpenAI 호환 /embeddings) 요청 생성·응답 검증. 선택 기능이며 기본은 꺼져 있다.

켜려면 EMBED_MODEL 을 지정한다 (예: build.nvidia.com 의 임베딩 모델 ID — 사용 가능 여부는 직접 확인).
임베딩은 '검색 결과의 순서'를 다듬는 데만 쓰이고, 어떤 논문이 후보가 되는지는 키워드 검색이 정한다.
네트워크 호출은 호출하는 쪽(서버: httpx, 수집 스크립트: urllib)이 맡는다.
"""
import math
import os
from dataclasses import dataclass
from typing import Any, Mapping

from vision import DEFAULT_BASE_URL

MAX_PASSAGE_CHARS = 1800


@dataclass(frozen=True)
class EmbedConfig:
    api_key: str
    base_url: str
    model: str  # 비어 있으면 비활성

    @property
    def enabled(self) -> bool:
        return bool(self.api_key and self.model)

    @classmethod
    def from_env(cls, env: Mapping[str, str] = os.environ) -> "EmbedConfig":
        key = env.get("EMBED_API_KEY") or env.get("VISION_API_KEY") or env.get("NVIDIA_API_KEY") or ""
        base = (env.get("EMBED_BASE_URL") or env.get("VISION_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        if not (base.startswith("https://") or base.startswith(("http://localhost", "http://127.0.0.1"))):
            raise ValueError("EMBED_BASE_URL 은 https:// 로 시작해야 합니다.")
        return cls(api_key=key, base_url=base, model=env.get("EMBED_MODEL", ""))


def build_request(cfg: EmbedConfig, texts: list[str], input_type: str) -> dict[str, Any]:
    """input_type: 'query' | 'passage'. NVIDIA 임베딩 모델은 이 구분이 필요하고, OpenAI 는 모르는 필드를 거부한다."""
    payload: dict[str, Any] = {
        "model": cfg.model,
        "input": [t[:MAX_PASSAGE_CHARS] for t in texts],
        "encoding_format": "float",
    }
    if "nvidia.com" in cfg.base_url:
        payload["input_type"] = input_type
        payload["truncate"] = "END"
    return payload


def normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm > 0 else vec


def parse_response(body: Any, expected: int) -> list[list[float]]:
    """응답 검증: 개수·차원·유한한 숫자 여부를 확인하고 단위벡터로 정규화해 돌려준다. 이상하면 ValueError."""
    try:
        rows = sorted(body["data"], key=lambda r: r.get("index", 0))
        vecs = [[float(x) for x in r["embedding"]] for r in rows]
    except (KeyError, TypeError, ValueError, AttributeError):
        raise ValueError("임베딩 응답 형식이 올바르지 않습니다.")
    if len(vecs) != expected:
        raise ValueError("임베딩 개수가 요청과 다릅니다.")
    dims = {len(v) for v in vecs}
    if len(dims) != 1 or 0 in dims:
        raise ValueError("임베딩 차원이 올바르지 않습니다.")
    if any(not math.isfinite(x) for v in vecs for x in v):
        raise ValueError("임베딩에 유효하지 않은 값이 있습니다.")
    return [normalize(v) for v in vecs]


def passage_text(title: str, abstract: str) -> str:
    return f"{title}. {abstract}"

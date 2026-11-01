#!/usr/bin/env python3
"""PubMed 에서 추천용 논문(메타분석/체계적 문헌고찰/RCT/리뷰)을 수집해 papers.db 에 저장한다.

내 PC 에서 실행한다 (인터넷 필요, 표준 라이브러리만 사용).

  python ingest_pubmed.py                         # 모든 토픽, 토픽당 30편
  python ingest_pubmed.py --topics volume,protein --per-topic 50
  python ingest_pubmed.py --email you@example.com --embed

환경변수: NCBI_API_KEY (선택, 있으면 속도 제한이 완화됨), BROCOMPASS_PAPERS_DB (저장 위치),
          --embed 사용 시 EMBED_MODEL 등 (embeddings.py 참고)
다시 실행해도 안전하다 (같은 PMID 는 갱신되고, 초록이 그대로면 임베딩도 유지된다).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Callable

import embeddings
import pubmed
from papers import PaperStore
from topics import TOPICS, pubmed_query

USER_AGENT = "BroCompass/0.4 (personal fitness project)"


def http_get(url: str, timeout: int = 30, retries: int = 3) -> str:
    last: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise
            last = e
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
        time.sleep(2 ** attempt)  # 1s, 2s, 4s
    raise RuntimeError(f"요청 실패: {last}")


def http_post_json(url: str, headers: dict, payload: dict, timeout: int = 60):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"detail": e.read().decode("utf-8", "replace")[:200]}


def ingest(
    store: PaperStore,
    topic_keys: list[str],
    per_topic: int,
    *,
    get: Callable[[str], str],
    sleep: Callable[[], None],
    api_key: str = "",
    email: str = "",
    log: Callable[[str], None] = print,
) -> dict[str, int]:
    """토픽별로 검색 -> 상세 조회 -> 저장. 한 토픽이 실패해도 나머지는 계속한다."""
    summary: dict[str, int] = {}
    seen: set[str] = set()
    for key in topic_keys:
        topic = TOPICS[key]
        log(f"[{key}] {topic.title}")
        try:
            ids = pubmed.parse_esearch(
                get(pubmed.esearch_url(pubmed_query(topic), per_topic, api_key=api_key, email=email))
            )
            sleep()
            new_ids = [i for i in ids if i not in seen]
            seen.update(ids)
            papers = []
            for i in range(0, len(new_ids), pubmed.MAX_IDS_PER_FETCH):
                chunk = new_ids[i : i + pubmed.MAX_IDS_PER_FETCH]
                papers += pubmed.parse_efetch(get(pubmed.efetch_url(chunk, api_key=api_key, email=email)))
                sleep()
            summary[key] = store.upsert(papers)
            log(f"    검색 {len(ids)}편 / 새로 저장 {summary[key]}편 (이미 받은 {len(ids) - len(new_ids)}편 제외)")
        except Exception as e:  # noqa: BLE001 — 토픽 단위로 격리
            summary[key] = 0
            log(f"    실패: {e}")
    return summary


def embed_missing(
    store: PaperStore, cfg: embeddings.EmbedConfig, post: Callable, log=print, batch: int = 16, pause: float = 1.6
) -> int:
    """임베딩이 없는 논문을 벡터화해 저장한다. 실패하면 중단하고 지금까지 저장한 수를 돌려준다."""
    done = 0
    while True:
        todo = store.missing_embeddings(limit=batch)
        if not todo:
            return done
        payload = embeddings.build_request(cfg, [embeddings.passage_text(p.title, p.abstract) for p in todo], "passage")
        status, body = post(
            f"{cfg.base_url}/embeddings",
            {"Authorization": f"Bearer {cfg.api_key}", "Content-Type": "application/json"},
            payload,
        )
        if status != 200:
            log(f"    임베딩 실패 (HTTP {status}): 모델 ID/권한을 확인하세요. 키워드 검색만으로도 추천은 동작합니다.")
            return done
        vecs = embeddings.parse_response(body, len(todo))
        store.set_embeddings({p.pmid: v for p, v in zip(todo, vecs)}, cfg.model)
        done += len(todo)
        log(f"    임베딩 {done}편 완료")
        time.sleep(pause)  # 무료 API 분당 한도(약 40회)를 넘지 않도록


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--topics", default="all", help=f"쉼표로 구분. 가능: {', '.join(TOPICS)} (기본: all)")
    ap.add_argument("--per-topic", type=int, default=30, help="토픽당 가져올 최대 논문 수 (기본 30)")
    ap.add_argument("--email", default=os.environ.get("NCBI_EMAIL", ""), help="NCBI 권장: 연락 가능한 이메일")
    ap.add_argument("--db", default=os.environ.get("BROCOMPASS_PAPERS_DB", os.path.join(os.path.dirname(__file__), "papers.db")))
    ap.add_argument("--embed", action="store_true", help="수집 후 임베딩도 생성 (EMBED_MODEL 필요)")
    args = ap.parse_args()

    keys = list(TOPICS) if args.topics == "all" else [k.strip() for k in args.topics.split(",") if k.strip()]
    unknown = [k for k in keys if k not in TOPICS]
    if unknown:
        print(f"알 수 없는 토픽: {', '.join(unknown)}\n가능: {', '.join(TOPICS)}", file=sys.stderr)
        return 2
    if not 1 <= args.per_topic <= 200:
        print("--per-topic 은 1~200 사이여야 합니다.", file=sys.stderr)
        return 2

    api_key = os.environ.get("NCBI_API_KEY", "")
    delay = 0.12 if api_key else 0.4  # 키 없이 초당 3회, 키가 있으면 초당 10회 한도 아래로
    store = PaperStore(args.db)
    print(f"저장 위치: {args.db}")
    ingest(store, keys, args.per_topic, get=http_get, sleep=lambda: time.sleep(delay),
           api_key=api_key, email=args.email)
    print(f"\n현재 논문 DB: {store.count()}편")

    if args.embed:
        cfg = embeddings.EmbedConfig.from_env()
        if not cfg.enabled:
            print("--embed 는 EMBED_MODEL 과 API 키 설정이 필요합니다. 건너뜁니다.", file=sys.stderr)
        else:
            print(f"\n임베딩 생성 ({cfg.model})")
            embed_missing(store, cfg, http_post_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

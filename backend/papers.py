"""논문 저장소 (SQLite, 표준 라이브러리만 사용).

초록/결론과 (선택) 임베딩 벡터를 저장한다. 검색은 retrieval.py 가 메모리에서 수행한다.
수천 편 규모까지는 이 방식으로 충분하며, 규모가 커지면 pgvector/Chroma 로 교체할 수 있다.
"""
import json
import sqlite3
import time
from contextlib import closing
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Paper:
    pmid: str
    title: str
    abstract: str
    conclusion: str = ""
    journal: str = ""
    year: Optional[int] = None
    doi: str = ""
    pub_types: list[str] = field(default_factory=list)
    authors: str = ""
    embedding: Optional[list[float]] = None


class PaperStore:
    def __init__(self, path: str):
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute(
            """
            create table if not exists papers (
                pmid        text primary key,
                title       text not null,
                abstract    text not null,
                conclusion  text not null default '',
                journal     text not null default '',
                year        integer,
                doi         text not null default '',
                pub_types   text not null default '[]',
                authors     text not null default '',
                fetched_at  integer not null,
                embedding   text,
                embed_model text
            )
            """
        )
        return conn

    def upsert(self, papers: list[Paper], now: Optional[int] = None) -> int:
        """저장한다. 초록이 바뀌지 않은 논문은 기존 임베딩을 유지하고, 바뀌었으면 비운다."""
        ts = int(now if now is not None else time.time())
        rows = [
            (p.pmid, p.title, p.abstract, p.conclusion, p.journal, p.year, p.doi,
             json.dumps(p.pub_types, ensure_ascii=False), p.authors, ts)
            for p in papers
        ]
        with closing(self._connect()) as conn, conn:
            conn.executemany(
                """
                insert into papers (pmid, title, abstract, conclusion, journal, year, doi,
                                    pub_types, authors, fetched_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(pmid) do update set
                    embedding   = case when papers.abstract = excluded.abstract then papers.embedding else null end,
                    embed_model = case when papers.abstract = excluded.abstract then papers.embed_model else null end,
                    title = excluded.title, abstract = excluded.abstract, conclusion = excluded.conclusion,
                    journal = excluded.journal, year = excluded.year, doi = excluded.doi,
                    pub_types = excluded.pub_types, authors = excluded.authors,
                    fetched_at = excluded.fetched_at
                """,
                rows,
            )
        return len(rows)

    @staticmethod
    def _row(r: tuple) -> Paper:
        emb = json.loads(r[10]) if r[10] else None
        return Paper(pmid=r[0], title=r[1], abstract=r[2], conclusion=r[3], journal=r[4], year=r[5],
                     doi=r[6], pub_types=json.loads(r[7]), authors=r[8], embedding=emb)

    _COLS = "pmid, title, abstract, conclusion, journal, year, doi, pub_types, authors, fetched_at, embedding"

    def all(self) -> list[Paper]:
        with closing(self._connect()) as conn:
            rows = conn.execute(f"select {self._COLS} from papers order by pmid").fetchall()
        return [self._row(r) for r in rows]

    def count(self) -> int:
        with closing(self._connect()) as conn:
            return conn.execute("select count(*) from papers").fetchone()[0]

    def version(self) -> tuple[int, int, int]:
        """(논문 수, 마지막 수집 시각, 임베딩 보유 수). 값이 같으면 메모리 색인을 다시 만들 필요가 없다."""
        with closing(self._connect()) as conn:
            return conn.execute(
                "select count(*), coalesce(max(fetched_at), 0), "
                "coalesce(sum(embedding is not null), 0) from papers"
            ).fetchone()

    def missing_embeddings(self, limit: int = 1000) -> list[Paper]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"select {self._COLS} from papers where embedding is null order by pmid limit ?", (limit,)
            ).fetchall()
        return [self._row(r) for r in rows]

    def set_embeddings(self, vectors: dict[str, list[float]], model: str) -> None:
        with closing(self._connect()) as conn, conn:
            conn.executemany(
                "update papers set embedding = ?, embed_model = ? where pmid = ?",
                [(json.dumps(v), model, pmid) for pmid, v in vectors.items()],
            )

    def embed_model(self) -> Optional[str]:
        """저장된 임베딩을 만든 모델. 질의 임베딩은 반드시 같은 모델이어야 한다."""
        with closing(self._connect()) as conn:
            row = conn.execute(
                "select embed_model from papers where embedding is not null limit 1"
            ).fetchone()
        return row[0] if row else None

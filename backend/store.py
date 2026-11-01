"""데일리 노트 저장소 (SQLite, 표준 라이브러리만 사용).

노트는 날짜별 JSON 문서 한 건으로 저장한다. 충돌 규칙은 '최신 updated_at 우선'이다.
Supabase/Postgres 로 옮길 때는 이 클래스와 같은 메서드(get/put/list_dates)를 구현하면 된다.
"""
import json
import sqlite3
from contextlib import closing
from typing import Any, Optional

Note = dict[str, Any]  # {"date": str, "blocks": list, "updated_at": int}


class NoteQuotaError(Exception):
    """한 사용자(owner)가 저장할 수 있는 노트 수를 넘었다."""


class NoteStore:
    """owner 는 사용자 구분 키다. 인증이 없는 로컬 실행은 기본값 ""(빈 문자열)을 쓰고,
    공개 배포에서는 브라우저가 만든 무작위 ID(X-Client-Id)를 넘겨 사용자끼리 노트를 분리한다."""

    def __init__(self, path: str, max_notes_per_owner: int = 1000):
        self.path = path
        self.max_notes_per_owner = max_notes_per_owner

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.execute(
            """
            create table if not exists user_notes (
                owner      text not null,
                date       text not null,
                body       text not null,
                updated_at integer not null,
                primary key (owner, date)
            )
            """
        )
        # 예전 버전(date 만 키였던 notes 표)의 기록은 owner "" 로 한 번만 옮기고 표 이름을 바꿔 둔다.
        legacy = conn.execute(
            "select 1 from sqlite_master where type='table' and name='notes'"
        ).fetchone()
        if legacy:
            with conn:
                conn.execute(
                    "insert or ignore into user_notes select '', date, body, updated_at from notes"
                )
                conn.execute("alter table notes rename to notes_legacy")
        return conn

    @staticmethod
    def _row_to_note(date: str, body: str, updated_at: int) -> Note:
        return {"date": date, "blocks": json.loads(body), "updated_at": updated_at}

    def get(self, date: str, owner: str = "") -> Optional[Note]:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "select body, updated_at from user_notes where owner = ? and date = ?",
                (owner, date),
            ).fetchone()
        return self._row_to_note(date, *row) if row else None

    def put(self, date: str, blocks: list[Any], updated_at: int, owner: str = "") -> Note:
        """더 최신인 경우에만 덮어쓰고, 항상 '이긴' 노트를 반환한다."""
        body = json.dumps(blocks, ensure_ascii=False)
        with closing(self._connect()) as conn, conn:  # 두 번째 conn: 트랜잭션 커밋
            exists = conn.execute(
                "select 1 from user_notes where owner = ? and date = ?", (owner, date)
            ).fetchone()
            if not exists:
                (n,) = conn.execute(
                    "select count(*) from user_notes where owner = ?", (owner,)
                ).fetchone()
                if n >= self.max_notes_per_owner:
                    raise NoteQuotaError(owner)
            # 조건부 upsert: 한 문장으로 처리해 동시 요청에서도 오래된 값이 덮어쓰지 못한다.
            conn.execute(
                """
                insert into user_notes (owner, date, body, updated_at) values (?, ?, ?, ?)
                on conflict(owner, date) do update
                    set body = excluded.body, updated_at = excluded.updated_at
                    where excluded.updated_at > user_notes.updated_at
                """,
                (owner, date, body, updated_at),
            )
            row = conn.execute(
                "select body, updated_at from user_notes where owner = ? and date = ?",
                (owner, date),
            ).fetchone()
        return self._row_to_note(date, *row)

    def list_dates(self, start: str, end: str, owner: str = "") -> list[str]:
        """start~end(포함) 사이에 블럭이 하나라도 있는 날짜 (오름차순)."""
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "select date, body from user_notes where owner = ? and date between ? and ? order by date",
                (owner, start, end),
            ).fetchall()
        return [d for d, body in rows if json.loads(body)]

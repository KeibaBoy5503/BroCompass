import sqlite3

import pytest

from store import NoteQuotaError, NoteStore


def test_owners_are_isolated(tmp_path):
    s = NoteStore(str(tmp_path / "t.db"))
    s.put("2026-11-01", [{"id": "a"}], 1, owner="alice-0000000000000")
    assert s.get("2026-11-01", owner="bob-000000000000000") is None
    assert s.get("2026-11-01") is None  # 기본 owner("")도 별개
    assert s.list_dates("2026-11-01", "2026-11-01", owner="alice-0000000000000") == ["2026-11-01"]
    assert s.list_dates("2026-11-01", "2026-11-01", owner="bob-000000000000000") == []


def test_same_date_different_owners_do_not_overwrite(tmp_path):
    s = NoteStore(str(tmp_path / "t.db"))
    s.put("2026-11-01", [{"id": "a"}], 100, owner="o1")
    won = s.put("2026-11-01", [{"id": "b"}], 50, owner="o2")  # o2 에게는 처음이므로 저장됨
    assert won["blocks"] == [{"id": "b"}]
    assert s.get("2026-11-01", owner="o1")["blocks"] == [{"id": "a"}]


def test_quota_blocks_new_dates_but_allows_update(tmp_path):
    s = NoteStore(str(tmp_path / "t.db"), max_notes_per_owner=2)
    s.put("2026-11-01", [{"id": 1}], 1, owner="o")
    s.put("2026-11-02", [{"id": 2}], 1, owner="o")
    with pytest.raises(NoteQuotaError):
        s.put("2026-11-03", [{"id": 3}], 1, owner="o")
    assert s.put("2026-11-02", [{"id": 9}], 5, owner="o")["blocks"] == [{"id": 9}]  # 기존 날짜 수정은 허용
    s.put("2026-11-03", [{"id": 3}], 1, owner="other")  # 다른 사용자는 영향 없음


def test_legacy_table_migrates_to_empty_owner(tmp_path):
    path = str(tmp_path / "old.db")
    conn = sqlite3.connect(path)
    conn.execute("create table notes (date text primary key, body text not null, updated_at integer not null)")
    conn.execute("insert into notes values ('2026-10-19', '[{\"id\": \"x\"}]', 7)")
    conn.commit()
    conn.close()
    s = NoteStore(path)
    assert s.get("2026-10-19") == {"date": "2026-10-19", "blocks": [{"id": "x"}], "updated_at": 7}
    assert s.get("2026-10-19", owner="someone") is None
    assert s.get("2026-10-19")["updated_at"] == 7  # 두 번째 연결에서도 정상(이름 변경 후)

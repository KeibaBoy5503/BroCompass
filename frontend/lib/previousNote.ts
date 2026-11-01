import { shiftDate } from "./date";
import { readLocal } from "./localNotes";
import { fetchNote, listNoteDates } from "./notesApi";
import type { DailyNote } from "./types";

const MAX_LOOKBACK_DAYS = 14;

/**
 * date 이전 가장 가까운, 블럭이 있는 노트를 찾는다 (최대 14일 전까지).
 * 이 기기(localStorage)와 서버를 모두 보고 더 가까운 날짜를 고르므로,
 * 다른 기기에서 쓴 어제 기록도 찾을 수 있다. 서버에 닿지 않으면 로컬만 사용한다.
 */
export async function findPreviousNote(date: string): Promise<DailyNote | null> {
  let local: DailyNote | null = null;
  for (let i = 1; i <= MAX_LOOKBACK_DAYS; i++) {
    const n = readLocal(shiftDate(date, -i));
    if (n && n.blocks.length > 0) {
      local = n;
      break;
    }
  }

  let remoteDate: string | null = null;
  try {
    const dates = await listNoteDates(shiftDate(date, -MAX_LOOKBACK_DAYS), shiftDate(date, -1));
    remoteDate = dates.length ? dates[dates.length - 1] : null; // 오름차순이므로 마지막이 가장 가까움
  } catch {
    /* 오프라인 */
  }

  // ISO 날짜 문자열은 사전순 = 시간순. 같은 날이면 로컬(이 기기의 최신 편집)을 우선한다.
  if (remoteDate && (!local || remoteDate > local.date)) {
    try {
      const remote = await fetchNote(remoteDate);
      if (remote && remote.blocks.length > 0) return remote;
    } catch {
      /* 서버 조회 실패 시 로컬 결과로 대체 */
    }
  }
  return local;
}

import type { DailyNote } from "./types";

const key = (date: string) => `brocompass:note:${date}`;

/** localStorage 에서 노트를 읽는다. 없거나 깨졌으면 null. (구버전 기록은 updatedAt = 0) */
export function readLocal(date: string): DailyNote | null {
  try {
    const raw = localStorage.getItem(key(date));
    if (!raw) return null;
    const p = JSON.parse(raw);
    if (!p || !Array.isArray(p.blocks)) return null;
    return {
      date,
      blocks: p.blocks,
      updatedAt: typeof p.updatedAt === "number" ? p.updatedAt : 0,
    };
  } catch {
    return null;
  }
}

export function writeLocal(note: DailyNote): void {
  try {
    localStorage.setItem(key(note.date), JSON.stringify(note));
  } catch {
    /* 저장 공간 부족/차단 시 메모리 상태만 유지 */
  }
}

const PREFIX = "brocompass:note:";

/** 이 기기에 저장된 모든 노트의 날짜(오름차순). 저장소를 못 읽으면 빈 배열. */
export function listLocalDates(): string[] {
  const dates: string[] = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k && k.startsWith(PREFIX)) {
        const d = k.slice(PREFIX.length);
        if (/^\d{4}-\d{2}-\d{2}$/.test(d)) dates.push(d);
      }
    }
  } catch {
    return [];
  }
  return dates.sort();
}

/** 이 기기의 블럭이 있는 모든 노트(오래된 순). 게임 통계(PR·스트릭·레벨) 계산용. */
export function loadAllLocal(): DailyNote[] {
  const out: DailyNote[] = [];
  for (const d of listLocalDates()) {
    const n = readLocal(d);
    if (n && n.blocks.length > 0) out.push(n);
  }
  return out;
}

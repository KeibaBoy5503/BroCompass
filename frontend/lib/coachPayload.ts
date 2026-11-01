import type { SuggestedBlock } from "./coachApi";
import { shiftDate } from "./date";
import { readLocal } from "./localNotes";
import { newId } from "./parse";
import type { DailyNote, WorkoutBlock } from "./types";

export const MAX_DAYS = 28;
export const MAX_BLOCKS_PER_DAY = 200;

/**
 * 기준일(포함)부터 거슬러 올라가 n일치 노트를 모아 서버에 보낼 형태로 만든다. 기록이 없는 날은 뺀다.
 * 이 기기(localStorage)의 기록만 사용한다. 오래된 순으로 정렬해 돌려준다.
 */
export function buildDays(
  endDate: string,
  n: number,
  read: (date: string) => DailyNote | null = readLocal
): { date: string; blocks: unknown[] }[] {
  const days: { date: string; blocks: unknown[] }[] = [];
  for (let i = 0; i < Math.min(Math.max(n, 1), MAX_DAYS); i++) {
    const date = shiftDate(endDate, -i);
    const note = read(date);
    if (note && note.blocks.length > 0) {
      days.push({ date, blocks: note.blocks.slice(0, MAX_BLOCKS_PER_DAY) });
    }
  }
  return days.reverse();
}

const clampInt = (v: unknown, lo: number, hi: number, fallback: number) =>
  typeof v === "number" && Number.isFinite(v) ? Math.min(hi, Math.max(lo, Math.round(v))) : fallback;

/** 서버가 제안한 운동을 노트에 넣을 운동 블럭으로 바꾼다. 서버 값은 믿지 않고 범위를 다시 제한한다. */
export function suggestionToBlock(s: SuggestedBlock): WorkoutBlock {
  return {
    id: newId(),
    kind: "workout",
    title: String(s.title ?? "").slice(0, 60) || "운동",
    plan: {
      sets: clampInt(s.sets, 1, 20, 3),
      reps: clampInt(s.reps, 1, 100, 10),
      weightKg: clampInt(s.weightKg, 0, 500, 0),
    },
    logs: [],
  };
}

/** 링크는 형식이 맞을 때만 만든다 (외부 데이터가 주소로 쓰이므로). */
export const pubmedUrl = (pmid: string) => (/^\d{1,9}$/.test(pmid) ? `https://pubmed.ncbi.nlm.nih.gov/${pmid}/` : null);
export const doiUrl = (doi: string) =>
  /^10\.\d{4,9}\/[^\s<>"]+$/.test(doi) ? `https://doi.org/${encodeURI(doi)}` : null;

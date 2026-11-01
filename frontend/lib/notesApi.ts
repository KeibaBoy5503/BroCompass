import { getClientId } from "./clientId";
import type { Block, DailyNote } from "./types";

const TIMEOUT_MS = 8000;

type Wire = { date: string; blocks: Block[]; updated_at: number };

async function request(url: string, init?: RequestInit): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const headers = { ...(init?.headers as Record<string, string> | undefined), "X-Client-Id": getClientId() };
    return await fetch(url, { ...init, headers, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

const fromWire = (w: Wire): DailyNote => ({
  date: w.date,
  blocks: w.blocks,
  updatedAt: w.updated_at,
});

/** 서버 노트 조회. 없으면 null, 서버 오류/오프라인이면 throw. */
export async function fetchNote(date: string): Promise<DailyNote | null> {
  const res = await request(`/api/notes/${date}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`노트 조회 실패 (${res.status})`);
  return fromWire(await res.json());
}

/** 노트 저장. 서버에 더 최신 노트가 있으면 저장되지 않고 그 노트가 반환된다. */
export async function pushNote(note: DailyNote): Promise<DailyNote> {
  const res = await request(`/api/notes/${note.date}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ blocks: note.blocks, updated_at: note.updatedAt }),
  });
  if (!res.ok) throw new Error(`노트 저장 실패 (${res.status})`);
  return fromWire(await res.json());
}

/** start~end 사이에 블럭이 있는 날짜 목록. */
export async function listNoteDates(start: string, end: string): Promise<string[]> {
  const res = await request(`/api/notes?start=${start}&end=${end}`);
  if (!res.ok) throw new Error(`날짜 조회 실패 (${res.status})`);
  return (await res.json()).dates as string[];
}

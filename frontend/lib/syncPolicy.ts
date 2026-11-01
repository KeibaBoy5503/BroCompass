import type { DailyNote } from "./types";

/**
 * 로컬 노트와 서버 노트를 비교해 무엇을 할지 결정한다. (순수 함수 — 테스트 가능)
 *  - adopt: 서버 것이 더 최신 → 서버 내용으로 교체
 *  - push : 로컬 것이 더 최신(또는 서버에 없음) → 서버로 올림
 *  - none : 같거나 할 일 없음
 */
export function decideSync(
  local: DailyNote,
  remote: DailyNote | null
): "adopt" | "push" | "none" {
  if (!remote) return local.blocks.length > 0 ? "push" : "none";
  if (remote.updatedAt > local.updatedAt) return "adopt";
  if (remote.updatedAt < local.updatedAt) return "push";
  return "none";
}

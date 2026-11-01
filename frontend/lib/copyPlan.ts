import { newId } from "./parse";
import type { Block } from "./types";

/**
 * 이전 날짜의 블럭을 오늘용 '계획'으로 복제한다.
 * 계획(plan)은 그대로 가져오고, 실제 수행 기록은 비운다 (세트 완료·섭취 체크 해제).
 * 새 id 를 부여하므로 원본 노트와 섞이지 않는다.
 */
export function cloneForToday(blocks: Block[]): Block[] {
  return blocks.map((b): Block => {
    const id = newId();
    switch (b.kind) {
      case "workout":
        return { ...b, id, plan: { ...b.plan }, logs: [] };
      case "meal":
        return { ...b, id, plan: { ...b.plan }, eatenAt: null };
      case "session":
        return { ...b, id, plan: { ...b.plan }, doneAt: null };
      default:
        return { ...b, id };
    }
  });
}

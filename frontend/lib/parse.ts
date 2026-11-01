import type { Block } from "./types";

let seq = 0;
export function newId(): string {
  seq += 1;
  return `b_${Date.now().toString(36)}_${seq}`;
}

const num = (s: string | undefined, fallback = 0) => {
  const n = Number(s);
  return Number.isFinite(n) ? n : fallback;
};

/**
 * 한 줄 입력을 블럭으로 변환한다. (블럭식 빠른 입력)
 *
 * 운동:  "벤치프레스 5x5 80"      -> 5세트 x 5회, 80kg
 *        "풀업 4x10"              -> 맨몸(0kg)
 * 식단:  "닭가슴살 200kcal p40"    -> 200kcal, 단백질 40g
 *        "현미밥 300kcal p6 c65 f2" -> 탄수 65g, 지방 2g
 * 그 외: 메모 블럭
 */
export function parseBlock(input: string): Block | null {
  const text = input.trim();
  if (!text) return null;

  // 세션: "NN분"(또는 "NN分", "NNmin") 토큰이 있으면 시간 기반 훈련 블럭. RPE 는 "rpe7" 형태로 적고, 없으면 6.
  //   "주짓수 스파링 60분 rpe7" -> 60분, RPE 7
  const minMatch = text.match(/(\d+(?:\.\d+)?)\s*(?:분|分|minutes?|mins?|min)(?![a-z])/i);
  if (minMatch) {
    const rpeMatch = text.match(/rpe\s*(\d+(?:\.\d+)?)/i);
    const title = (text.slice(0, minMatch.index) + " " + text.slice((minMatch.index ?? 0) + minMatch[0].length))
      .replace(/rpe\s*\d+(?:\.\d+)?/i, "")
      .replace(/\s+/g, " ")
      .trim();
    return {
      id: newId(),
      kind: "session",
      title: title || "세션",
      plan: {
        minutes: Math.min(Math.max(num(minMatch[1], 1), 1), 600),
        rpe: Math.min(Math.max(num(rpeMatch?.[1], 6), 1), 10),
      },
      doneAt: null,
    };
  }

  // 식단: kcal 토큰이 있으면 식단 블럭
  const kcalMatch = text.match(/(\d+(?:\.\d+)?)\s*kcal/i);
  if (kcalMatch) {
    const title = text.slice(0, kcalMatch.index).trim() || "식단";
    const rest = text.slice((kcalMatch.index ?? 0) + kcalMatch[0].length);
    const grab = (key: string) => {
      const m = rest.match(new RegExp(`\\b${key}\\s*(\\d+(?:\\.\\d+)?)`, "i"));
      return num(m?.[1]);
    };
    return {
      id: newId(),
      kind: "meal",
      title,
      plan: {
        kcal: num(kcalMatch[1]),
        proteinG: grab("p"),
        carbG: grab("c"),
        fatG: grab("f"),
      },
      eatenAt: null,
    };
  }

  // 운동: "NxM" 토큰이 있으면 운동 블럭
  const setMatch = text.match(/(\d+)\s*[x×*]\s*(\d+)/i);
  if (setMatch) {
    const title = text.slice(0, setMatch.index).trim() || "운동";
    const rest = text.slice((setMatch.index ?? 0) + setMatch[0].length);
    const w = rest.match(/(\d+(?:\.\d+)?)\s*(?:kg)?/i);
    return {
      id: newId(),
      kind: "workout",
      title,
      plan: {
        sets: Math.min(Math.max(num(setMatch[1], 1), 1), 20),
        reps: num(setMatch[2], 1),
        weightKg: num(w?.[1]),
      },
      logs: [],
    };
  }

  return { id: newId(), kind: "text", title: text };
}

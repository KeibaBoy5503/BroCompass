export type Confidence = "high" | "medium" | "low";

export type DetectedItem = {
  name: string;
  kcal: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  /** AI 가 추정한 1회 제공량(g). 모를 때는 null */
  grams?: number | null;
  confidence?: Confidence | null;
  /** 탄단지로 계산한 칼로리(4/4/9) */
  macro_kcal?: number | null;
};

export type MealAnalysis = {
  items: DetectedItem[];
  note: string;
  warnings: string[];
  model: string;
};

const TIMEOUT_MS = 90_000;

/** 압축된 사진(base64, data: 접두사 없음)을 서버에 보내 음식 항목과 영양 추정치를 받는다. */
export async function analyzeMeal(
  image: string,
  mime: string,
  signal?: AbortSignal,
  hint?: string,
  lang: "ko" | "ja" | "en" = "ko"
): Promise<MealAnalysis> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  signal?.addEventListener("abort", () => ctrl.abort(), { once: true });

  let res: Response;
  try {
    res = await fetch("/api/meal/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image, mime, hint: hint ?? "", lang }),
      signal: ctrl.signal,
    });
  } catch (e) {
    if (signal?.aborted) throw e; // 사용자가 직접 취소한 경우는 호출한 쪽에서 처리
    throw new Error("서버에 연결하지 못했어요. 백엔드가 켜져 있는지 확인해 주세요.");
  } finally {
    clearTimeout(timer);
  }

  if (!res.ok) {
    let detail = "";
    try {
      const j = await res.json();
      if (typeof j?.detail === "string") detail = j.detail; // 검증 오류(422)는 배열이라 건너뜀
    } catch {
      /* 본문이 JSON 이 아님 */
    }
    throw new Error(detail || `사진을 분석하지 못했어요 (${res.status})`);
  }
  return (await res.json()) as MealAnalysis;
}

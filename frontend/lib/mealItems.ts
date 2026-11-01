import type { Confidence } from "./mealApi";
import { newId } from "./parse";
import type { MealBlock } from "./types";

/** 검토 화면에서 편집 중인 한 줄. 입력 도중 빈 칸/소수점을 허용하려고 숫자를 문자열로 들고 있다. */
export type DraftRow = {
  key: string;
  name: string;
  kcal: string;
  protein: string;
  carb: string;
  fat: string;
  /** AI 가 추정한 제공량(g), 배율을 곱하기 전 값 */
  grams: number | null;
  confidence: Confidence | null;
  /** AI 가 준 원래 값. 배율 버튼은 항상 이 값에 곱한다 (여러 번 눌러도 오차가 쌓이지 않는다) */
  base: { kcal: number; protein: number; carb: number; fat: number };
  /** 현재 선택된 배율. 값을 직접 고치면 null */
  scale: number | null;
};

type Detected = {
  name: string;
  kcal: number;
  protein_g: number;
  carb_g: number;
  fat_g: number;
  grams?: number | null;
  confidence?: Confidence | null;
};

export const SCALES = [0.5, 0.75, 1, 1.25, 1.5, 2] as const;
export const MISMATCH_RATIO = 0.25; // 서버(vision.py)의 경고 기준과 같다

export function toDraftRows(items: Detected[]): DraftRow[] {
  return items.map((it) => ({
    key: newId(),
    name: it.name,
    kcal: String(it.kcal),
    protein: String(it.protein_g),
    carb: String(it.carb_g),
    fat: String(it.fat_g),
    grams: it.grams ?? null,
    confidence: it.confidence ?? null,
    base: { kcal: it.kcal, protein: it.protein_g, carb: it.carb_g, fat: it.fat_g },
    scale: 1,
  }));
}

/** AI 가 준 값에 배율을 곱해 칼로리·탄단지를 한꺼번에 바꾼다. (0.5 = 절반만 먹음, 2 = 두 배) */
export function applyScale(row: DraftRow, scale: number): DraftRow {
  const r1 = (n: number) => String(Math.round(n * scale * 10) / 10);
  return {
    ...row,
    scale,
    kcal: String(Math.round(row.base.kcal * scale)),
    protein: r1(row.base.protein),
    carb: r1(row.base.carb),
    fat: r1(row.base.fat),
  };
}

/** 배율을 반영한 제공량(g). 값을 직접 고쳐서 배율이 없어졌거나 AI 가 제공량을 주지 않았으면 null. */
export function scaledGrams(row: DraftRow): number | null {
  return row.grams && row.scale ? Math.round(row.grams * row.scale) : null;
}

/** 현재 입력된 탄단지로 계산한 칼로리 (단백질·탄수 4, 지방 9 kcal/g) */
export function macroKcal(row: DraftRow): number {
  return 4 * toAmount(row.protein) + 4 * toAmount(row.carb) + 9 * toAmount(row.fat);
}

/** 칼로리와 탄단지 계산값이 크게 어긋나는지 */
export function kcalMismatch(row: DraftRow): boolean {
  const k = toAmount(row.kcal);
  const m = macroKcal(row);
  return k > 0 && m > 0 && Math.abs(k - m) / Math.max(k, m) > MISMATCH_RATIO;
}

export function kcalFromMacros(row: DraftRow): DraftRow {
  return { ...row, kcal: String(Math.round(macroKcal(row))), scale: null };
}

/** 문자열 -> 0 이상의 유한한 수 (소수 첫째 자리). 비었거나 잘못된 값은 0. */
export function toAmount(s: string): number {
  const n = Number(s.replace(",", ".").trim());
  return Number.isFinite(n) && n > 0 ? Math.round(Math.min(n, 100000) * 10) / 10 : 0;
}

/**
 * 검토를 마친 행을 식단 블럭으로 바꾼다. 이름이 없거나 칼로리·탄단지가 모두 0인 행은 버린다.
 * eaten=true 면 사진으로 기록한 '먹은 것'으로 처리해 섭취 완료(Actual) 상태로 넣는다.
 */
export function rowsToBlocks(rows: DraftRow[], eaten: boolean, now = Date.now()): MealBlock[] {
  const blocks: MealBlock[] = [];
  for (const r of rows) {
    const title = r.name.trim().slice(0, 60);
    const plan = {
      kcal: toAmount(r.kcal),
      proteinG: toAmount(r.protein),
      carbG: toAmount(r.carb),
      fatG: toAmount(r.fat),
    };
    if (!title || plan.kcal + plan.proteinG + plan.carbG + plan.fatG === 0) continue;
    blocks.push({ id: newId(), kind: "meal", title, plan, eatenAt: eaten ? now : null });
  }
  return blocks;
}

export function totalKcal(rows: DraftRow[]): number {
  return rows.reduce((s, r) => s + toAmount(r.kcal), 0);
}

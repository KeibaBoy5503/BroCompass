// 계산기 결과를 다른 화면(다이어트 도우미 등)에서 쓰기 위해 이 기기에 저장해 둔다.

const KEY = "brocompass:calc-profile";

export type CalcProfile = {
  tdee: number;
  weightKg: number;
  bodyFatPct?: number;
  savedAt: number;
};

const ok = (v: unknown, lo: number, hi: number): v is number =>
  typeof v === "number" && Number.isFinite(v) && v >= lo && v <= hi;

/** 값이 정상 범위일 때만 저장한다. 저장소를 못 쓰면 조용히 무시한다. */
export function saveCalcProfile(p: Omit<CalcProfile, "savedAt">, now = Date.now()): void {
  if (!ok(p.tdee, 500, 10000) || !ok(p.weightKg, 20, 400)) return;
  const out: CalcProfile = { tdee: Math.round(p.tdee), weightKg: p.weightKg, savedAt: now };
  if (ok(p.bodyFatPct, 2, 70)) out.bodyFatPct = p.bodyFatPct;
  try {
    localStorage.setItem(KEY, JSON.stringify(out));
  } catch {
    /* 무시 */
  }
}

export function readCalcProfile(): CalcProfile | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const p = JSON.parse(raw);
    if (!p || !ok(p.tdee, 500, 10000) || !ok(p.weightKg, 20, 400) || !ok(p.savedAt, 0, Number.MAX_SAFE_INTEGER)) return null;
    return { tdee: p.tdee, weightKg: p.weightKg, bodyFatPct: ok(p.bodyFatPct, 2, 70) ? p.bodyFatPct : undefined, savedAt: p.savedAt };
  } catch {
    return null;
  }
}

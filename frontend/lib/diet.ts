// 다이어트 도우미 계산. 화면과 무관한 순수 함수.
// 가정: 제지방량(근육·뼈 등)은 그대로 유지하고 체지방만 줄어든다. 실제로는 근손실이 조금 있을 수 있다.

export const KCAL_PER_KG_FAT = 7700; // 체지방 1kg 대략 7,700kcal (흔히 쓰는 근사값)

export type DietInput = {
  weightKg: number;
  bodyFatPct: number;
  targetBodyFatPct: number;
  maintenanceKcal: number; // 유지 칼로리(TDEE)
  weeklyLossPct: number; // 주당 감량 속도 (체중 대비 %)
};

/** 번역 키(한국어 원문)와 채울 값. 화면에서 t(key, vars) 로 바꿔 보여준다. */
export type DietWarning = { key: string; vars?: Record<string, number> };

export type DietPlan = {
  leanKg: number;
  fatKg: number;
  targetWeightKg: number;
  loseKg: number;
  weeklyLossKg: number;
  dailyDeficit: number;
  dailyIntake: number;
  deficitPct: number; // 유지 칼로리 대비 부족분 %
  weeks: number;
  days: number;
  curve: number[]; // 0주차부터 주별 예상 체중
  warnings: DietWarning[];
};

export type DietResult = { ok: true; plan: DietPlan } | { ok: false; error: string };

export const LIMITS = {
  weight: [30, 300],
  bodyFat: [3, 60],
  maintenance: [1000, 6000],
  weeklyPct: [0.25, 1.5],
} as const;

const inRange = (v: number, [lo, hi]: readonly [number, number] | readonly number[]) =>
  Number.isFinite(v) && v >= lo && v <= hi;

const round1 = (n: number) => Math.round(n * 10) / 10;

export function planDiet(i: DietInput): DietResult {
  if (!inRange(i.weightKg, LIMITS.weight)) return { ok: false, error: "체중은 30~300kg 사이로 입력해 주세요." };
  if (!inRange(i.bodyFatPct, LIMITS.bodyFat)) return { ok: false, error: "현재 체지방률은 3~60% 사이로 입력해 주세요." };
  if (!inRange(i.targetBodyFatPct, LIMITS.bodyFat)) return { ok: false, error: "목표 체지방률은 3~60% 사이로 입력해 주세요." };
  if (i.targetBodyFatPct >= i.bodyFatPct) return { ok: false, error: "목표 체지방률은 현재보다 낮아야 해요." };
  if (!inRange(i.maintenanceKcal, LIMITS.maintenance)) return { ok: false, error: "유지 칼로리는 1,000~6,000kcal 사이로 입력해 주세요." };
  if (!inRange(i.weeklyLossPct, LIMITS.weeklyPct)) return { ok: false, error: "주당 감량 속도는 0.25~1.5% 사이로 입력해 주세요." };

  const leanKg = i.weightKg * (1 - i.bodyFatPct / 100);
  const fatKg = i.weightKg - leanKg;
  const targetWeightKg = leanKg / (1 - i.targetBodyFatPct / 100);
  const loseKg = i.weightKg - targetWeightKg;

  const weeklyLossKg = (i.weightKg * i.weeklyLossPct) / 100;
  const dailyDeficit = (weeklyLossKg * KCAL_PER_KG_FAT) / 7;
  const dailyIntake = i.maintenanceKcal - dailyDeficit;
  const deficitPct = (dailyDeficit / i.maintenanceKcal) * 100;
  const weeks = Math.ceil(loseKg / weeklyLossKg);
  const days = Math.ceil((loseKg / weeklyLossKg) * 7);

  const curve: number[] = [];
  for (let w = 0; w <= weeks; w++) curve.push(round1(Math.max(i.weightKg - weeklyLossKg * w, targetWeightKg)));

  const warnings: DietWarning[] = [];
  if (i.weeklyLossPct > 1) warnings.push({ key: "주당 1%를 넘는 감량은 근손실 위험이 커져요. 속도를 줄이는 걸 고려해 보세요." });
  if (deficitPct > 25) warnings.push({ key: "하루 부족분이 유지 칼로리의 {pct}%예요. 25%를 넘으면 유지하기 어렵고 근손실 위험이 커져요.", vars: { pct: Math.round(deficitPct) } });
  if (dailyIntake < 1200) warnings.push({ key: "목표 섭취량이 1,200kcal 미만이에요. 의료진 관리 없이 이렇게 낮추는 건 권하지 않아요." });
  if (i.targetBodyFatPct < 10) warnings.push({ key: "체지방률 10% 미만은 유지가 어렵고 호르몬·컨디션에 부담이 될 수 있어요." });

  return {
    ok: true,
    plan: {
      leanKg: round1(leanKg),
      fatKg: round1(fatKg),
      targetWeightKg: round1(targetWeightKg),
      loseKg: round1(loseKg),
      weeklyLossKg: Math.round(weeklyLossKg * 100) / 100,
      dailyDeficit: Math.round(dailyDeficit),
      dailyIntake: Math.round(dailyIntake),
      deficitPct: round1(deficitPct),
      weeks,
      days,
      curve,
      warnings,
    },
  };
}

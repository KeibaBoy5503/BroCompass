export type CalcInput = {
  sex: "male" | "female";
  age: number;
  height_cm: number;
  weight_kg: number;
  activity: "sedentary" | "light" | "moderate" | "active" | "very_active";
  goal: "cut" | "maintain" | "bulk";
  body_type: "ectomorph" | "mesomorph" | "endomorph";
  body_fat_pct?: number;
};

export type CalcResult = {
  bmr: number;
  tdee: number;
  target_kcal: number;
  carb_g: number;
  protein_g: number;
  fat_g: number;
};

export async function fetchCalc(input: CalcInput): Promise<CalcResult> {
  const res = await fetch("/api/calc", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) throw new Error("계산 요청에 실패했습니다. 입력값을 확인해주세요.");
  return res.json();
}

"""BroCompass 계산 로직: BMR / TDEE / 목표 칼로리 / 탄단지 분배."""
from dataclasses import dataclass

ACTIVITY_FACTORS = {
    "sedentary": 1.2,       # 거의 운동 안 함
    "light": 1.375,         # 주 1~3회
    "moderate": 1.55,       # 주 3~5회
    "active": 1.725,        # 주 6~7회
    "very_active": 1.9,     # 하루 2회 / MMA 등 고강도 병행
}

# 목표별 칼로리 조정 비율
GOAL_ADJUST = {
    "cut": -0.20,
    "maintain": 0.0,
    "bulk": 0.10,
}

# 체형(체질) 기반 탄단지 비율 (탄, 단, 지) - 단백질은 별도로 체중 기준 보정
BODY_TYPE_SPLIT = {
    "ectomorph": (0.50, 0.25, 0.25),
    "mesomorph": (0.40, 0.30, 0.30),
    "endomorph": (0.30, 0.35, 0.35),
}

KCAL_PER_G = {"carb": 4, "protein": 4, "fat": 9}


@dataclass
class Result:
    bmr: float
    tdee: float
    target_kcal: float
    carb_g: float
    protein_g: float
    fat_g: float


def bmr_mifflin(sex: str, weight_kg: float, height_cm: float, age: int) -> float:
    """Mifflin-St Jeor 공식."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def bmr_katch(weight_kg: float, body_fat_pct: float) -> float:
    """Katch-McArdle 공식 (체지방률을 알 때 더 정확)."""
    lbm = weight_kg * (1 - body_fat_pct / 100)
    return 370 + 21.6 * lbm


def calculate(
    sex: str,
    age: int,
    height_cm: float,
    weight_kg: float,
    activity: str,
    goal: str,
    body_type: str,
    body_fat_pct: float | None = None,
) -> Result:
    bmr = (
        bmr_katch(weight_kg, body_fat_pct)
        if body_fat_pct is not None
        else bmr_mifflin(sex, weight_kg, height_cm, age)
    )
    tdee = bmr * ACTIVITY_FACTORS[activity]
    target = tdee * (1 + GOAL_ADJUST[goal])

    carb_r, prot_r, fat_r = BODY_TYPE_SPLIT[body_type]
    protein_g = target * prot_r / KCAL_PER_G["protein"]

    # 단백질 최소 보장: 체중 1.6g/kg (근비대 메타분석 기준 하한 근사치)
    protein_min = 1.6 * weight_kg
    if protein_g < protein_min:
        protein_g = protein_min

    remaining = max(target - protein_g * KCAL_PER_G["protein"], 0)
    carb_share = carb_r / (carb_r + fat_r)
    carb_g = remaining * carb_share / KCAL_PER_G["carb"]
    fat_g = remaining * (1 - carb_share) / KCAL_PER_G["fat"]

    return Result(
        bmr=round(bmr, 1),
        tdee=round(tdee, 1),
        target_kcal=round(target, 1),
        carb_g=round(carb_g, 1),
        protein_g=round(protein_g, 1),
        fat_g=round(fat_g, 1),
    )

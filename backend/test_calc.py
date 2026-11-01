import pytest
from fastapi.testclient import TestClient

import calc
from main import app

client = TestClient(app)


def test_mifflin_male():
    # 10*80 + 6.25*180 - 5*30 + 5 = 1780
    assert calc.bmr_mifflin("male", 80, 180, 30) == pytest.approx(1780)


def test_mifflin_female():
    # 10*60 + 6.25*165 - 5*25 - 161 = 1345.25
    assert calc.bmr_mifflin("female", 60, 165, 25) == pytest.approx(1345.25)


def test_katch():
    # LBM 64 -> 370 + 21.6*64 = 1752.4
    assert calc.bmr_katch(80, 20) == pytest.approx(1752.4)


def test_goal_adjustment():
    base = dict(sex="male", age=30, height_cm=180, weight_kg=80,
                activity="moderate", body_type="mesomorph")
    cut = calc.calculate(goal="cut", **base)
    bulk = calc.calculate(goal="bulk", **base)
    assert cut.target_kcal < cut.tdee < bulk.target_kcal


def test_macros_match_calories():
    r = calc.calculate("male", 30, 180, 80, "moderate", "maintain", "mesomorph")
    kcal = r.carb_g * 4 + r.protein_g * 4 + r.fat_g * 9
    assert kcal == pytest.approx(r.target_kcal, abs=5)


def test_protein_floor():
    r = calc.calculate("female", 25, 160, 90, "sedentary", "cut", "ectomorph")
    assert r.protein_g >= 1.6 * 90 - 0.1


def test_api():
    res = client.post("/api/calc", json={
        "sex": "male", "age": 30, "height_cm": 180, "weight_kg": 80,
        "activity": "moderate", "goal": "bulk", "body_type": "mesomorph",
    })
    assert res.status_code == 200
    assert res.json()["target_kcal"] > res.json()["tdee"]


def test_api_validation():
    res = client.post("/api/calc", json={"sex": "male", "age": 5})
    assert res.status_code == 422

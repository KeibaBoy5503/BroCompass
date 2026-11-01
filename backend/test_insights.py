# 기록 분석 테스트. 입력은 모두 직접 만든 가짜 기록이다.
import insights
from insights import analyze, classify


def W(title, sets, reps, weight, done=None):
    n = sets if done is None else done
    return {"id": "w", "kind": "workout", "title": title, "plan": {"sets": sets, "reps": reps, "weightKg": weight},
            "logs": [{"setIndex": i, "completedAt": 1} for i in range(n)]}


def M(title, kcal, protein, eaten=True):
    return {"id": "m", "kind": "meal", "title": title, "eatenAt": 1 if eaten else None,
            "plan": {"kcal": kcal, "proteinG": protein, "carbG": 0, "fatG": 0}}


def T(text):
    return {"id": "t", "kind": "text", "title": text}


def D(day, *blocks):
    return {"date": day, "blocks": list(blocks)}


def ids(a):
    return [i["id"] for i in a.insights]


def get(a, id_):
    return next(i for i in a.insights if i["id"] == id_)


PUSH_HEAVY = [
    D("2026-10-14", W("벤치프레스", 5, 5, 80), W("오버헤드프레스", 3, 8, 40), W("케이블 푸쉬다운", 3, 12, 20)),
    D("2026-10-16", W("인클라인 벤치프레스", 4, 8, 60), W("랫풀다운", 3, 10, 50), W("케이블 푸쉬다운", 3, 12, 20)),
    D("2026-10-18", W("벤치프레스", 3, 5, 80)),
]


def test_classify_names():
    table = {
        "벤치프레스": "chest", "Bench Press": "chest", "인클라인 덤벨 프레스": "chest", "덤벨 플라이": "chest",
        "랫풀다운": "back", "Pull-up": "back", "바벨 로우": "back", "데드리프트": "back",
        "리어델트 플라이": "shoulders_rear", "Face Pull": "shoulders_rear",
        "사이드 레터럴 레이즈": "shoulders_side", "숄더 프레스": "shoulders_front", "Overhead Press": "shoulders_front",
        "레그 컬": "hamstrings", "루마니안 데드리프트": "hamstrings", "스쿼트": "quads", "레그프레스": "quads",
        "Hip Thrust": "glutes", "카프 레이즈": "calves", "케이블 푸쉬다운": "triceps", "스컬크러셔": "triceps",
        "덤벨 컬": "biceps", "해머컬": "biceps", "플랭크": "abs", "MMA 스파링": None, "러닝": None, "": None,
    }
    for name, want in table.items():
        assert classify(name) == want, (name, classify(name), want)


def test_push_heavy_week_flags_imbalance_and_rear_delts():
    a = analyze(PUSH_HEAVY)
    assert a.stats["basis"] == "done" and a.stats["enough_data"]
    assert (a.stats["push_sets"], a.stats["pull_sets"]) == (21, 3)
    assert ids(a)[:1] == ["push_pull"]
    rear = get(a, "low_volume:shoulders_rear")
    assert rear["severity"] == "medium" and rear["topics"] == ["rear_delt", "volume"]
    assert rear["suggested_blocks"] == [{"title": "리어델트 플라이", "sets": 4, "reps": 15, "weightKg": 0}]
    # 당기기가 부족할 때는 당기기 근육군(후면 삼각근·이두)이 먼저 뽑힌다
    assert [i for i in ids(a) if i.startswith("low_volume")][:2] == ["low_volume:shoulders_rear", "low_volume:biceps"]
    assert len([i for i in ids(a) if i.startswith("low_volume")]) == insights.MAX_LOW_VOLUME
    assert "체중을 입력하면" in " ".join(a.stats["hints"])
    assert get(a, "push_pull")["suggested_blocks"][0]["title"] == "랫풀다운"


def test_uses_plan_when_nothing_completed():
    days = [D(d["date"], *[{**b, "logs": []} if b["kind"] == "workout" else b for b in d["blocks"]]) for d in PUSH_HEAVY]
    a = analyze(days)
    assert a.stats["basis"] == "plan" and "계획한" in get(a, "push_pull")["detail"]


def test_balanced_week_has_no_volume_flags():
    day = lambda n: D(f"2026-10-{n}", W("벤치프레스", 10, 8, 60), W("랫풀다운", 10, 8, 50), W("리어델트 플라이", 10, 12, 8),
                      W("사이드 레터럴 레이즈", 10, 12, 8), W("덤벨 컬", 10, 12, 10), W("케이블 푸쉬다운", 10, 12, 20),
                      W("스쿼트", 10, 8, 80), W("레그 컬", 10, 12, 30))
    a = analyze([day(15)])
    assert a.insights == [] and a.stats["enough_data"]


def test_insufficient_data_skips_volume_but_not_other_rules():
    a = analyze([D("2026-10-19", W("벤치프레스", 2, 5, 60), T("오늘 어깨 통증 있음"))])
    assert not a.stats["enough_data"] and ids(a) == ["pain:shoulder"]
    assert any("미만" in h for h in a.stats["hints"])


def test_pain_detection_and_negation():
    assert ids(analyze([D("2026-10-19", T("오늘 어깨 통증 있음"))])) == ["pain:shoulder"]
    assert ids(analyze([D("2026-10-19", T("어깨 통증 없음"))])) == []
    assert ids(analyze([D("2026-10-19", T("무릎 괜찮음"))])) == []
    assert ids(analyze([D("2026-10-19", T("허리 아픔"))])) == ["pain:low_back"]
    assert ids(analyze([D("2026-10-19", T("knee pain after squats"))])) == ["pain:knee"]
    assert ids(analyze([D("2026-10-19", T("shoulder was pain-free today"))])) == []
    assert ids(analyze([D("2026-10-19", T("어깨 운동 열심히"))])) == []  # 부위만 언급, 통증 단어 없음
    p = get(analyze([D("2026-10-19", T("어깨 충돌 느낌"))]), "pain:shoulder")
    assert p["severity"] == "high" and p["topics"] == ["shoulder_pain"] and "전문가" in p["detail"]


def test_pain_has_highest_priority():
    a = analyze(PUSH_HEAVY[:2] + [D("2026-10-18", T("어깨 불편함"))])
    assert ids(a)[0] == "pain:shoulder"


def test_protein():
    meals = lambda p: [D(f"2026-10-{d}", M("식사", 600, p)) for d in (15, 16, 17)]
    a = analyze(meals(100), weight_kg=80)
    assert "1.2g/kg" in get(a, "protein")["detail"] and get(a, "protein")["topics"] == ["protein"]
    assert "protein" not in ids(analyze(meals(150), weight_kg=80))        # 1.9g/kg -> 정상
    assert "protein" not in ids(analyze(meals(100)[:2], weight_kg=80))    # 2일치 -> 판단 보류
    assert any("3일 미만" in h for h in analyze(meals(100)[:2], weight_kg=80).stats["hints"])
    assert "체중을 입력" in " ".join(analyze(meals(100)).stats["hints"])
    skipped = [D(f"2026-10-{d}", M("식사", 600, 100, eaten=False)) for d in (15, 16, 17)]
    assert "protein" not in ids(analyze(skipped, weight_kg=80))           # 먹지 않은 식단은 제외


def test_plateau_detection():
    bench = lambda day, w: D(day, W("벤치프레스", 3, 5, w))
    stalled = analyze([bench("2026-10-05", 80), bench("2026-10-08", 80), bench("2026-10-12", 80)])
    p = get(stalled, "plateau:벤치프레스")
    assert p["kind"] == "plateau" and p["topics"] == ["plateau"] and "1200" in p["detail"]
    assert "plateau:벤치프레스" not in ids(analyze([bench("2026-10-05", 80), bench("2026-10-08", 82.5), bench("2026-10-12", 85)]))
    assert "plateau:벤치프레스" not in ids(analyze([bench("2026-10-05", 80), bench("2026-10-08", 80)]))  # 2회는 판단 보류
    # 마지막 이틀 중 하나라도 이전 최고를 넘으면 정체가 아니다
    assert "plateau:벤치프레스" not in ids(analyze([bench("2026-10-05", 80), bench("2026-10-08", 77.5), bench("2026-10-12", 82.5)]))
    # 맨몸 운동은 횟수로 비교
    pull = lambda day, reps: D(day, W("풀업", 3, reps, 0))
    assert "plateau:풀업" in ids(analyze([pull("2026-10-05", 8), pull("2026-10-08", 8), pull("2026-10-12", 7)]))


def test_combat_and_conditioning():
    a = analyze([D("2026-10-19", T("MMA 스파링 3라운드"))])
    assert get(a, "combat")["topics"] == ["combat", "concurrent"] and get(a, "combat")["severity"] == "info"
    assert get(analyze([D("2026-10-19", T("러닝 5km"))]), "combat")["topics"] == ["concurrent"]
    assert ids(analyze([D("2026-10-19", W("스파링", 5, 3, 0, done=0))])) == ["combat"]
    assert "combat" not in ids(analyze(PUSH_HEAVY))


def test_caps_and_ordering():
    days = PUSH_HEAVY + [D("2026-10-19", T("어깨 통증"), T("무릎 아픔"), T("허리 불편"), T("MMA 스파링"))]
    a = analyze(days, weight_kg=80)
    assert len(a.insights) <= insights.MAX_INSIGHTS
    ranks = [insights._SEVERITY_RANK[i["severity"]] for i in a.insights]
    assert ranks == sorted(ranks) and a.insights[0]["severity"] == "high"
    assert len(set(ids(a))) == len(ids(a))  # id 중복 없음


def test_garbage_input_never_raises():
    nan = float("nan")
    junk = [None, 5, "x", {"date": "bad"}, {"date": "2026-02-30", "blocks": [T("x")]}, {"date": "2026-10-19", "blocks": "str"},
            {"date": "2026-10-19", "blocks": [1, None, [], {"kind": "workout", "title": None, "plan": "x", "logs": 5},
             {"kind": "workout", "title": "벤치", "plan": {"sets": -3, "reps": "a", "weightKg": nan}, "logs": [{"reps": -1}, None]},
             {"kind": "workout", "title": "스쿼트", "plan": {"sets": 10**9, "reps": 10**9, "weightKg": 10**9}, "logs": [{}] * 100},
             {"kind": "meal", "plan": None, "eatenAt": 1}, {"kind": "meal", "plan": {"proteinG": "NaN"}, "eatenAt": 5},
             {"kind": "text", "title": 12345}, {"kind": "text", "title": "어깨 통증\x00\x1f" * 500}]}]
    a = analyze(junk, weight_kg=80)
    assert isinstance(a.insights, list)
    for i in a.insights:
        assert len(i["detail"]) < 600
    assert analyze("junk").insights == [] and analyze([]).insights == [] and analyze(None).insights == []
    assert analyze([]).stats["days_with_data"] == 0


# ---- 격투기/컨디셔닝 세션 부하 (Phase 6) ----------------------------------------------

def S(title, minutes, rpe, done=True):
    return {"id": "s", "kind": "session", "title": title, "doneAt": 1 if done else None,
            "plan": {"minutes": minutes, "rpe": rpe}}


def test_session_load_in_combat_card_and_stats():
    a = analyze([D("2026-10-27", S("주짓수 스파링", 60, 7)), D("2026-10-29", S("러닝", 30, 5))])
    assert "combat" in ids(a)
    assert a.stats["session_load"] == {"count": 2, "minutes": 90, "week_au": 570, "prev_au": 0}
    assert "570 AU" in get(a, "combat")["detail"]
    assert get(a, "combat")["topics"] == ["combat", "concurrent"]


def test_undone_or_invalid_sessions_are_ignored():
    a = analyze([D("2026-10-27", S("주짓수 스파링", 60, 7, done=False), S("복싱", 0, 7), S("복싱", 60, 0),
                   S("", 60, 7), {"kind": "session", "title": "x", "plan": "bad", "doneAt": 1})])
    assert a.stats["session_load"]["count"] == 0
    assert "load_spike" not in ids(a)


def test_load_spike_needs_enough_previous_load_and_ratio():
    prev = D("2026-10-21", S("주짓수 스파링", 60, 6))                                 # 360 AU
    spike = [prev, D("2026-10-28", S("주짓수 스파링", 60, 8), S("복싱", 30, 8))]        # 720 AU = 2.0x
    a = analyze(spike)
    assert get(a, "load_spike")["severity"] == "medium"
    assert "2.0배" in get(a, "load_spike")["detail"]
    # 1.5배 이하는 경고 없음
    assert "load_spike" not in ids(analyze([prev, D("2026-10-28", S("주짓수 스파링", 60, 9))]))  # 540 = 1.5x
    # 직전 부하가 너무 작으면(300 AU 미만) 비율이 커도 경고하지 않음
    assert "load_spike" not in ids(analyze([D("2026-10-21", S("러닝", 20, 5)), D("2026-10-28", S("스파링", 90, 9))]))


def test_hard_days_counts_distinct_days():
    three = [D(f"2026-10-{d}", S("스파링", 40, 8)) for d in (24, 26, 28)]
    assert "hard_days" in ids(analyze(three))
    # 같은 날 두 번은 하루로 센다
    two_days = [D("2026-10-24", S("스파링", 40, 9), S("복싱", 30, 8)), D("2026-10-28", S("스파링", 40, 8))]
    assert "hard_days" not in ids(analyze(two_days))
    # RPE 7 은 고강도로 보지 않는다
    assert "hard_days" not in ids(analyze([D(f"2026-10-{d}", S("스파링", 40, 7)) for d in (24, 26, 28)]))


# ---- 오타 허용 / 일본어·영어 이름 ----------------------------------------------------------

def test_classify_typos_and_languages():
    cases = {
        "래터럴 레이즈": "shoulders_side", "사이드 라터럴 레이즈": "shoulders_side", "사이드 레터럴": "shoulders_side",
        "Lateral Raise": "shoulders_side", "サイドレイズ": "shoulders_side",
        "벤치프래스": "chest", "ベンチプレス": "chest", "Bench Press": "chest",
        "스쿼드": "quads", "スクワット": "quads", "Back Squat": "quads",
        "데드리프": "back", "デッドリフト": "back", "랫플다운": "back", "ラットプルダウン": "back", "Lat Pulldown": "back",
        "ルーマニアンデッドリフト": "hamstrings", "レッグカール": "hamstrings", "懸垂": "back",
        "ダンベルカール": "biceps", "리어델트 플라이": "shoulders_rear", "リアデルト": "shoulders_rear",
        "プッシュダウン": "triceps", "腹筋": "abs",
    }
    for title, muscle in cases.items():
        assert classify(title) == muscle, title


def test_fuzzy_does_not_overreach():
    for title in ["주짓수 스파링", "러닝", "어깨 아픔", "점심 먹기", "휴식", "스트레칭", "요가"]:
        assert classify(title) is None, title
    # 정확히 맞는 키워드가 오타 일치보다 우선한다
    assert classify("레그컬") == "hamstrings"
    assert classify("바벨컬") == "biceps"


def test_japanese_combat_and_conditioning():
    a = analyze([D("2026-10-27", S("柔術スパーリング", 60, 7)), D("2026-10-29", S("ランニング", 30, 5))])
    assert get(a, "combat")["topics"] == ["combat", "concurrent"]

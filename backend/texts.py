"""서버가 만드는 문장(코치 인사이트, 사진 분석 경고 등)의 한국어·일본어·영어 문구표.

한국어 문구는 이 모듈을 만들기 전의 출력과 같은 글자로 유지한다 (기존 테스트와 화면이 그대로 동작한다).
알 수 없는 언어 코드는 한국어로 처리하고, 문구가 빠져 있으면 한국어 문구로 대체한다.
"""

from __future__ import annotations

LANGS = ("ko", "ja", "en")
LANG_NAME = {"ko": "Korean", "ja": "Japanese", "en": "English"}


def norm_lang(v: object) -> str:
    return v if isinstance(v, str) and v in LANGS else "ko"


# 키 -> {언어: 템플릿}. 템플릿은 str.format 형식이다.
_T: dict[str, dict[str, str]] = {
    "no_data": {
        "ko": "분석할 기록이 없어요.",
        "ja": "分析する記録がありません。",
        "en": "There are no records to analyze.",
    },
    "pain_title": {
        "ko": "{label} 불편감이 기록돼 있어요",
        "ja": "{label}の不快感が記録されています",
        "en": "Discomfort in your {label} is logged",
    },
    "pain_detail": {
        "ko": "{date} 메모에 {label} 관련 불편/통증 언급이 있어요. 통증이 계속되거나 심해지면 운동을 줄이고 의사·물리치료사 등 전문가와 상담하세요.",
        "ja": "{date}のメモに{label}の不快感・痛みに関する記述があります。痛みが続く、または強くなる場合は運動を減らし、医師や理学療法士などの専門家に相談してください。",
        "en": "Your note on {date} mentions discomfort or pain in your {label}. If it persists or gets worse, cut back on training and consult a doctor or physical therapist.",
    },
    "pushpull_title": {
        "ko": "밀기 운동에 비해 당기기 운동이 적어요",
        "ja": "プッシュ種目に比べてプル種目が少ないです",
        "en": "Pulling volume is low compared with pushing",
    },
    "pushpull_detail": {
        "ko": "최근 7일 {basis} 세트: 밀기 {push}세트 vs 당기기 {pull}세트 (휴리스틱 기준 비율 {ratio}배 초과).",
        "ja": "直近7日の{basis}セット: プッシュ{push}セット vs プル{pull}セット（目安の比率{ratio}倍超）。",
        "en": "Last 7 days, {basis} sets: push {push} vs pull {pull} (above the heuristic ratio of {ratio}x).",
    },
    "lowvol_title": {
        "ko": "{muscle} 운동량이 적어 보여요",
        "ja": "{muscle}のトレーニング量が少なそうです",
        "en": "{muscle} volume looks low",
    },
    "lowvol_detail": {
        "ko": "최근 7일 {basis} {muscle} 세트 {n}개 (휴리스틱 기준 주 {min}세트 이상).",
        "ja": "直近7日の{basis}{muscle}セットは{n}セット（目安: 週{min}セット以上）。",
        "en": "Last 7 days: {n} {basis} {muscle} sets (heuristic: at least {min} sets per week).",
    },
    "hint_few_sets": {
        "ko": "최근 7일 운동 기록이 {n}세트 미만이라 운동량 분석은 건너뛰었어요.",
        "ja": "直近7日の運動記録が{n}セット未満のため、トレーニング量の分析はスキップしました。",
        "en": "Fewer than {n} sets logged in the last 7 days, so volume analysis was skipped.",
    },
    "protein_title": {
        "ko": "단백질 섭취가 적을 수 있어요",
        "ja": "タンパク質の摂取が少ないかもしれません",
        "en": "Protein intake may be low",
    },
    "protein_detail": {
        "ko": "식단을 기록한 {days}일 평균 단백질 {avg:.0f}g ({gkg:.1f}g/kg, 체중 {w:g}kg 기준). 휴리스틱 하한 {floor}g/kg. 기록이 빠진 끼니가 있으면 실제보다 낮게 보일 수 있어요.",
        "ja": "食事を記録した{days}日間の平均タンパク質は{avg:.0f}g（{gkg:.1f}g/kg、体重{w:g}kg換算）。目安の下限は{floor}g/kgです。記録漏れの食事があると、実際より低く見えることがあります。",
        "en": "Average protein over the {days} days with logged meals: {avg:.0f} g ({gkg:.1f} g/kg at {w:g} kg). Heuristic floor: {floor} g/kg. Missing meals in your log can make this look lower than it really is.",
    },
    "hint_weight": {
        "ko": "체중을 입력하면 단백질 섭취도 분석해요.",
        "ja": "体重を入力すると、タンパク質摂取も分析します。",
        "en": "Enter your weight to also analyze protein intake.",
    },
    "hint_protein_days": {
        "ko": "섭취 완료로 기록한 식단이 {n}일 미만이라 단백질 분석은 건너뛰었어요.",
        "ja": "摂取済みとして記録した食事が{n}日未満のため、タンパク質の分析はスキップしました。",
        "en": "Meals marked as eaten cover fewer than {n} days, so protein analysis was skipped.",
    },
    "plateau_title": {
        "ko": "'{name}' 진전이 멈춘 것 같아요",
        "ja": "「{name}」の伸びが止まっているようです",
        "en": "'{name}' seems to have stalled",
    },
    "plateau_detail": {
        "ko": "'{name}' 최근 {n}회 기록에서 볼륨(횟수×중량)이 이전 최고 기록을 넘지 못했어요 (이전 최고 {before:.0f}, 최근 {recent:.0f}).",
        "ja": "「{name}」の直近{n}回の記録で、ボリューム（回数×重量）が過去最高を超えていません（過去最高 {before:.0f}、直近 {recent:.0f}）。",
        "en": "In the last {n} sessions of '{name}', volume (reps × weight) did not beat your previous best (previous best {before:.0f}, recent {recent:.0f}).",
    },
    "combat_title": {
        "ko": "{what} 훈련을 병행하고 있어요",
        "ja": "{what}のトレーニングを併用しています",
        "en": "You are also doing {what} training",
    },
    "combat_detail": {
        "ko": "최근 기록에 {what} 훈련이 포함돼 있어요. 근력 운동과 병행할 때의 회복·간섭 효과에 관한 근거를 모았어요.",
        "ja": "直近の記録に{what}のトレーニングが含まれています。筋力トレーニングと併用した場合の回復・干渉効果に関する根拠を集めました。",
        "en": "Your recent log includes {what} training. We gathered evidence on recovery and interference effects when combining it with strength training.",
    },
    "combat_sessions": {
        "ko": " 최근 7일 완료한 세션 {n}회, 총 {m}분, 세션 부하 {au} AU (분×RPE).",
        "ja": " 直近7日に完了したセッションは{n}回、合計{m}分、セッション負荷は{au} AU（分×RPE）です。",
        "en": " Sessions completed in the last 7 days: {n}, {m} min in total, session load {au} AU (minutes × RPE).",
    },
    "what_combat": {"ko": "격투기", "ja": "格闘技", "en": "combat sports"},
    "what_cond": {"ko": "유산소/컨디셔닝", "ja": "有酸素・コンディショニング", "en": "cardio/conditioning"},
    "load_spike_title": {
        "ko": "훈련 부하가 갑자기 늘었어요",
        "ja": "トレーニング負荷が急に増えました",
        "en": "Training load jumped suddenly",
    },
    "load_spike_detail": {
        "ko": "세션 부하가 직전 7일 {prev:.0f} AU에서 최근 7일 {cur:.0f} AU로 {ratio:.1f}배가 됐어요 (휴리스틱 기준 {limit}배 초과). 부하가 급격히 늘면 부상 위험과 회복 부담이 커질 수 있어요.",
        "ja": "セッション負荷が直前7日の{prev:.0f} AUから直近7日の{cur:.0f} AUへ、{ratio:.1f}倍になりました（目安の{limit}倍超）。負荷が急に増えると、ケガのリスクや回復の負担が大きくなることがあります。",
        "en": "Session load rose from {prev:.0f} AU in the previous 7 days to {cur:.0f} AU in the last 7 days ({ratio:.1f}x, above the heuristic {limit}x). A sharp rise can increase injury risk and recovery demands.",
    },
    "hard_days_title": {
        "ko": "고강도 세션이 여러 날 이어졌어요",
        "ja": "高強度のセッションが何日も続いています",
        "en": "Several hard sessions in a row",
    },
    "hard_days_detail": {
        "ko": "최근 7일 중 {n}일에 RPE {rpe} 이상 세션이 있었어요 (휴리스틱 기준 {limit}일 이상). 회복일이 충분한지 살펴보세요.",
        "ja": "直近7日のうち{n}日にRPE {rpe}以上のセッションがありました（目安: {limit}日以上）。回復日が十分か確認してください。",
        "en": "{n} of the last 7 days had sessions with RPE {rpe} or higher (heuristic: {limit}+ days). Check that you have enough recovery days.",
    },
    "basis_done": {"ko": "완료한", "ja": "完了した", "en": "completed"},
    "basis_plan": {"ko": "계획한", "ja": "計画した", "en": "planned"},
    "disclaimer": {
        "ko": "참고용 정보이며 의료·영양 전문가의 조언을 대체하지 않아요. 통증이나 부상이 있으면 전문가와 상담하세요. AI 요약은 원문 초록과 다를 수 있으니 논문을 직접 확인하세요.",
        "ja": "参考情報であり、医療・栄養の専門家の助言に代わるものではありません。痛みやケガがある場合は専門家に相談してください。AI要約は原文の抄録と異なる場合があるため、論文を直接確認してください。",
        "en": "For reference only; this does not replace advice from a medical or nutrition professional. If you have pain or an injury, consult a professional. AI summaries can differ from the original abstract, so check the papers yourself.",
    },
    "llm_parse": {
        "ko": "AI 요약을 해석하지 못했어요. 논문 목록만 보여드릴게요.",
        "ja": "AI要約を解釈できませんでした。論文リストのみ表示します。",
        "en": "Could not parse the AI summary. Showing the paper list only.",
    },
    "w_macro_calc": {
        "ko": "{name}: 칼로리를 탄단지로 계산했어요.",
        "ja": "{name}: カロリーをPFCから計算しました。",
        "en": "{name}: calories were calculated from the macros.",
    },
    "w_mismatch": {
        "ko": "{name}: 칼로리({kcal:.0f})와 탄단지로 계산한 값({macro:.0f})이 서로 맞지 않아요. 확인해 주세요.",
        "ja": "{name}: カロリー（{kcal:.0f}）とPFCから計算した値（{macro:.0f}）が合っていません。確認してください。",
        "en": "{name}: calories ({kcal:.0f}) and the value computed from macros ({macro:.0f}) do not match. Please check.",
    },
    "w_low_conf": {
        "ko": "{name}: AI가 확신하지 못했어요. 음식 이름과 양을 확인해 주세요.",
        "ja": "{name}: AIの確信度が低いです。食品名と量を確認してください。",
        "en": "{name}: the AI was not confident. Please check the food name and amount.",
    },
}

MUSCLE_LABELS: dict[str, dict[str, str]] = {
    "ko": {"chest": "가슴", "back": "등", "shoulders_front": "전면 삼각근", "shoulders_side": "측면 삼각근",
           "shoulders_rear": "후면 삼각근", "biceps": "이두", "triceps": "삼두", "quads": "대퇴사두",
           "hamstrings": "햄스트링", "glutes": "둔근", "calves": "종아리", "abs": "복근"},
    "ja": {"chest": "胸", "back": "背中", "shoulders_front": "三角筋前部", "shoulders_side": "三角筋中部",
           "shoulders_rear": "三角筋後部", "biceps": "上腕二頭筋", "triceps": "上腕三頭筋", "quads": "大腿四頭筋",
           "hamstrings": "ハムストリング", "glutes": "臀筋", "calves": "ふくらはぎ", "abs": "腹筋"},
    "en": {"chest": "chest", "back": "back", "shoulders_front": "front delts", "shoulders_side": "side delts",
           "shoulders_rear": "rear delts", "biceps": "biceps", "triceps": "triceps", "quads": "quads",
           "hamstrings": "hamstrings", "glutes": "glutes", "calves": "calves", "abs": "abs"},
}

REGION_LABELS: dict[str, dict[str, str]] = {
    "ko": {"shoulder": "어깨", "knee": "무릎", "low_back": "허리"},
    "ja": {"shoulder": "肩", "knee": "膝", "low_back": "腰"},
    "en": {"shoulder": "shoulder", "knee": "knee", "low_back": "lower back"},
}

# 부족한 근육군에 추가를 제안하는 운동 이름. 이름만 언어별로 바뀌고 세트·횟수는 insights.py 에 있다.
SUGGEST_NAMES: dict[str, dict[str, str]] = {
    "ko": {"chest": "덤벨 벤치프레스", "back": "랫풀다운", "shoulders_side": "사이드 레터럴 레이즈",
           "shoulders_rear": "리어델트 플라이", "biceps": "덤벨 컬", "triceps": "케이블 푸쉬다운",
           "quads": "레그프레스", "hamstrings": "라잉 레그컬"},
    "ja": {"chest": "ダンベルベンチプレス", "back": "ラットプルダウン", "shoulders_side": "サイドレイズ",
           "shoulders_rear": "リアデルトフライ", "biceps": "ダンベルカール", "triceps": "ケーブルプッシュダウン",
           "quads": "レッグプレス", "hamstrings": "ライイングレッグカール"},
    "en": {"chest": "Dumbbell Bench Press", "back": "Lat Pulldown", "shoulders_side": "Lateral Raise",
           "shoulders_rear": "Rear Delt Fly", "biceps": "Dumbbell Curl", "triceps": "Cable Pushdown",
           "quads": "Leg Press", "hamstrings": "Lying Leg Curl"},
}


def tx(lang: str, key: str, **kw: object) -> str:
    entry = _T[key]
    text = entry.get(norm_lang(lang)) or entry["ko"]
    return text.format(**kw) if kw else text


def muscle_label(lang: str, key: str) -> str:
    return MUSCLE_LABELS[norm_lang(lang)][key]

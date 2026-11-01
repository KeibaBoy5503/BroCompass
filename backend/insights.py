"""운동·식단 기록에서 '살펴볼 점(insight)'을 규칙으로 찾아낸다. 외부 호출이 없는 순수 로직이다.

여기서 쓰는 기준값(주당 세트 수, 단백질 g/kg 등)은 널리 알려진 경험칙에 기댄 휴리스틱이며 개인 처방이 아니다.
추천 화면에서는 이 규칙이 찾아낸 '현상'만 보여주고, 그에 대한 과학적 근거는 검색한 논문에서 가져온다.
입력은 클라이언트가 보낸 신뢰할 수 없는 JSON 이므로, 모든 필드를 방어적으로 읽는다.
"""
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional
from texts import REGION_LABELS, SUGGEST_NAMES, muscle_label, norm_lang, tx

# ---- 휴리스틱 기준값 ------------------------------------------------------------
MIN_WEEKLY_SETS = 10        # 주요 근육군의 주당 세트 수 하한 (근비대 경험칙)
PUSH_PULL_RATIO = 1.5       # 밀기:당기기 세트 비가 이 값을 넘으면 불균형으로 본다
PROTEIN_G_PER_KG = 1.6      # 하루 단백질 섭취 하한 (g/체중kg)
MIN_TOTAL_SETS = 6          # 이보다 기록이 적으면 운동량 분석은 하지 않는다
MIN_PROTEIN_DAYS = 3        # 단백질은 최소 이 일수의 식단 기록이 있어야 판단한다
MIN_PLATEAU_SESSIONS = 3
MAX_INSIGHTS = 8
# 세션 RPE 부하(분 x RPE, 단위 AU). 급증 판단은 직전 7일 부하가 충분히 있을 때만 한다.
LOAD_SPIKE_RATIO = 1.5
LOAD_SPIKE_MIN_PREV_AU = 300
HARD_RPE = 8
HARD_DAYS_LIMIT = 3
MAX_LOW_VOLUME = 3
MAX_PLATEAU = 2

MUSCLE_LABEL = {
    "chest": "가슴", "back": "등", "shoulders_front": "전면 삼각근", "shoulders_side": "측면 삼각근",
    "shoulders_rear": "후면 삼각근", "biceps": "이두", "triceps": "삼두", "quads": "대퇴사두",
    "hamstrings": "햄스트링", "glutes": "둔근", "calves": "종아리", "abs": "복근",
}
PUSH = {"chest", "shoulders_front", "shoulders_side", "triceps"}
PULL = {"back", "shoulders_rear", "biceps"}
# 운동량 부족을 점검할 주요 근육군 (전면 삼각근은 밀기 운동으로 충분히 자극되므로 제외)
MAJOR = ["chest", "back", "shoulders_side", "shoulders_rear", "biceps", "triceps", "quads", "hamstrings"]

# 먼저 나온 규칙이 우선한다 (구체적인 이름을 앞에: '레그컬'이 '컬'보다, '리어델트 플라이'가 '플라이'보다 먼저).
_MUSCLE_RULES: list[tuple[str, list[str]]] = [
    ("shoulders_rear", ["리어델트", "후면삼각", "페이스풀", "facepull", "reversefly", "리버스플라이", "벤트오버레이즈", "reardelt", "リアデルト", "リアレイズ", "フェイスプル", "リバースフライ", "後部三角筋", "リアーデルト", "rearlateral"]),
    ("shoulders_side", ["사이드레터럴", "레터럴레이즈", "사레레", "lateralraise", "sidelateral", "측면삼각", "레터럴", "래터럴", "라터럴", "lateral", "사이드래터럴", "사이드레이즈", "sideraise", "サイドレイズ", "ラテラルレイズ", "サイドラテラル", "側部三角筋"]),
    ("shoulders_front", ["숄더프레스", "오버헤드프레스", "밀리터리", "ohp", "overheadpress", "shoulderpress", "프론트레이즈", "frontraise", "아놀드", "ショルダープレス", "オーバーヘッドプレス", "ミリタリープレス", "フロントレイズ", "アーノルド", "숄더프래스"]),
    ("hamstrings", ["레그컬", "legcurl", "루마니안", "romanian", "rdl", "굿모닝", "햄스트링", "스티프레그", "レッグカール", "ルーマニアンデッドリフト", "ハムストリング", "ハムストリングス"]),
    ("quads", ["스쿼트", "squat", "레그프레스", "legpress", "런지", "lunge", "레그익스텐션", "legextension", "대퇴사두", "스쿼드", "스콰트", "스퀏", "スクワット", "レッグプレス", "ランジ", "レッグエクステンション", "大腿四頭筋", "hacksquat", "핵스쿼트"]),
    ("glutes", ["힙쓰러스트", "hipthrust", "글루트", "glute", "ヒップスラスト", "グルート", "臀筋", "힙쓰러스", "힙트러스트"]),
    ("calves", ["카프", "calf", "종아리", "カーフレイズ", "ふくらはぎ"]),
    ("triceps", ["푸쉬다운", "푸시다운", "pushdown", "트라이셉", "tricep", "스컬크러셔", "skullcrusher", "삼두", "딥스", "dips", "プッシュダウン", "トライセップ", "スカルクラッシャー", "ディップス", "三頭筋", "フレンチプレス", "프렌치프레스", "frenchpress", "킥백", "kickback", "キックバック"]),
    ("biceps", ["바벨컬", "덤벨컬", "해머컬", "컬", "curl", "이두", "바이셉", "bicep", "カール", "二頭筋", "프리처컬", "preachercurl", "プリーチャーカール"]),
    ("chest", ["벤치프레스", "벤치", "bench", "체스트", "인클라인프레스", "inclinepress", "덤벨프레스", "dumbbellpress", "가슴", "푸쉬업", "푸시업", "pushup", "펙덱", "pecdeck", "플라이", "fly", "크로스오버", "ベンチプレス", "ベンチ", "インクラインプレス", "ダンベルプレス", "チェスト", "腕立て", "プッシュアップ", "ペックデック", "フライ", "ケーブルクロスオーバー", "胸", "벤치프래스", "벤치푸레스", "체스트프레스", "chestpress"]),
    ("back", ["풀업", "턱걸이", "pullup", "chinup", "랫풀", "latpull", "풀다운", "pulldown", "로우", "row", "데드리프트", "deadlift", "懸垂", "チンニング", "ラットプルダウン", "プルダウン", "ロウ", "ローイング", "ベントオーバーロー", "デッドリフト", "背中", "랫플다운", "래풀다운", "랫풀다운", "풀다은", "데드리프", "pullover", "풀오버", "시티드로우", "シーテッドロー"]),
    ("abs", ["크런치", "crunch", "플랭크", "plank", "레그레이즈", "legraise", "복근", "싯업", "situp", "クランチ", "プランク", "レッグレイズ", "腹筋", "シットアップ", "アブローラー", "abwheel", "앱휠", "행잉레그레이즈"]),
]
_COMBAT = ["mma", "스파링", "주짓수", "bjj", "복싱", "킥복싱", "무에타이", "레슬링", "유도", "샌드백", "sparring", "boxing", "muaythai", "grappling", "スパーリング", "柔術", "ボクシング", "キックボクシング", "ムエタイ", "レスリング", "柔道", "サンドバッグ", "ブラジリアン柔術", "스파링"]
_CONDITIONING = ["러닝", "런닝", "달리기", "조깅", "인터벌", "hiit", "로잉", "사이클", "싸이클", "줄넘기", "버피", "ランニング", "ジョギング", "ロードワーク", "縄跳び", "バーピー", "running", "jogging", "hiit"]

_REGIONS = {  # 키 -> (표시 이름, 본문 키워드, topics 키)
    "shoulder": ("어깨", ["어깨", "shoulder"], "shoulder_pain"),
    "knee": ("무릎", ["무릎", "knee"], "knee_pain"),
    "low_back": ("허리", ["허리", "low back", "lower back"], "low_back_pain"),
}
_PAIN = re.compile(r"통증|아프|아픔|불편|충돌|욱신|시큰|결림|impingement|pain|sore ?ness|hurt")
_NEGATION = re.compile(r"없|안 ?아|괜찮|나았|좋아졌|no pain|pain[- ]?free|painless|not hurt")

# 부족한 근육군에 대한 추가 운동 제안 (제목, 세트, 횟수). 근거가 아니라 단순 예시이며 사용자가 고쳐 쓴다.
_SUGGEST = {
    "chest": ("덤벨 벤치프레스", 3, 10), "back": ("랫풀다운", 3, 10), "shoulders_side": ("사이드 레터럴 레이즈", 3, 15),
    "shoulders_rear": ("리어델트 플라이", 3, 15), "biceps": ("덤벨 컬", 3, 12), "triceps": ("케이블 푸쉬다운", 3, 12),
    "quads": ("레그프레스", 3, 10), "hamstrings": ("라잉 레그컬", 3, 12),
}
_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2, "info": 3}


# ---- 방어적 읽기 -------------------------------------------------------------------

def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9가-힣぀-ヿ一-龥ー]", "", s.lower())


def _str(v: Any, limit: int = 200) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", v)[:limit].strip() if isinstance(v, str) else ""


def _num(v: Any, default: float = 0.0, hi: float = 100000.0) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
        return default
    return min(float(v), hi)


def _date(v: Any) -> Optional[date]:
    try:
        return date.fromisoformat(v) if isinstance(v, str) and len(v) == 10 else None
    except ValueError:
        return None


FUZZY_MIN_LEN = 5  # 이 길이 이상인 키워드만 오타(글자 1개 차이)를 허용한다. 짧은 단어는 오탐이 많다.


def _dist_le1(a: str, b: str) -> bool:
    """편집 거리(삽입·삭제·교체)가 1 이하인가."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    i = 0
    while i < min(len(a), len(b)) and a[i] == b[i]:
        i += 1
    if len(a) == len(b):
        return a[i + 1:] == b[i + 1:]
    short, long_ = (a, b) if len(a) < len(b) else (b, a)
    return short[i:] == long_[i + 1:]


def _near(n: str, key: str) -> bool:
    if len(key) < FUZZY_MIN_LEN:
        return False
    for size in (len(key) - 1, len(key), len(key) + 1):
        for i in range(0, len(n) - size + 1):
            if _dist_le1(n[i:i + size], key):
                return True
    return False


def classify(title: str) -> Optional[str]:
    """운동 이름 -> 근육군. 먼저 정확히 포함되는 키워드를 찾고, 없을 때만 오타를 허용해 다시 찾는다."""
    n = _norm(title)
    for muscle, keys in _MUSCLE_RULES:
        if any(k in n for k in keys):
            return muscle
    for muscle, keys in _MUSCLE_RULES:
        if any(_near(n, k) for k in keys):
            return muscle
    return None


def _set_volume(reps: float, weight: float) -> float:
    return reps * weight if weight > 0 else reps  # 맨몸 운동은 횟수만으로 비교


@dataclass
class _Workout:
    day: date
    title: str
    key: str
    muscle: Optional[str]
    planned: int
    done: int
    volume: float  # 완료한 세트 기준


def _read_workout(day: date, b: dict) -> Optional[_Workout]:
    title = _str(b.get("title"), 60)
    plan = b.get("plan") if isinstance(b.get("plan"), dict) else {}
    p_sets = int(min(_num(plan.get("sets")), 20))
    p_reps, p_w = _num(plan.get("reps")), _num(plan.get("weightKg"))
    logs = [l for l in (b.get("logs") if isinstance(b.get("logs"), list) else [])[:20] if isinstance(l, dict)]
    volume = sum(
        _set_volume(_num(l.get("reps"), p_reps) if l.get("reps") is not None else p_reps,
                    _num(l.get("weightKg"), p_w) if l.get("weightKg") is not None else p_w)
        for l in logs
    )
    if not title or (p_sets == 0 and not logs):
        return None
    return _Workout(day, title, _norm(title), classify(title), p_sets, len(logs), volume)


@dataclass
class _Session:
    day: date
    title: str
    minutes: float
    rpe: float
    combat: bool

    @property
    def load(self) -> float:
        return self.minutes * self.rpe


def _read_session(day: date, b: dict) -> Optional[_Session]:
    """격투기/유산소 세션 블럭. 완료(doneAt)한 것만 부하에 센다. 값은 범위를 다시 제한한다."""
    plan = b.get("plan") if isinstance(b.get("plan"), dict) else {}
    title = _str(b.get("title"), 60)
    minutes, rpe = _num(plan.get("minutes"), 0.0, 600.0), _num(plan.get("rpe"), 0.0, 10.0)
    if not title or not b.get("doneAt") or minutes <= 0 or rpe <= 0:
        return None
    n = _norm(title)
    return _Session(day, title, minutes, rpe, any(k in n for k in _COMBAT))


@dataclass
class Analysis:
    insights: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


def _insight(id_: str, kind: str, severity: str, title: str, detail: str, topics: list[str],
             suggested: Optional[list[dict]] = None) -> dict:
    return {"id": id_, "kind": kind, "severity": severity, "title": title, "detail": detail,
            "topics": topics, "suggested_blocks": suggested or []}


def _suggest_block(group: str, deficit: float, lang: str = "ko") -> list[dict]:
    if group not in _SUGGEST:
        return []
    _, sets, reps = _SUGGEST[group]
    name = SUGGEST_NAMES[norm_lang(lang)].get(group) or _SUGGEST[group][0]
    sets = max(2, min(4, math.ceil(deficit / 2))) if deficit > 0 else sets
    return [{"title": name, "sets": sets, "reps": reps, "weightKg": 0}]


def analyze(days: list[dict], weight_kg: Optional[float] = None, lang: str = "ko") -> Analysis:
    """days: [{"date": "YYYY-MM-DD", "blocks": [...]}] -> 분석 결과. 어떤 입력에도 예외를 던지지 않는다.
    lang: 결과 문장의 언어 (ko/ja/en). 알 수 없는 값은 한국어로 처리한다."""
    lang = norm_lang(lang)
    parsed: list[tuple[date, list[dict]]] = []
    for d in days if isinstance(days, list) else []:
        if not isinstance(d, dict):
            continue
        dt = _date(d.get("date"))
        blocks = [b for b in (d.get("blocks") if isinstance(d.get("blocks"), list) else [])[:200] if isinstance(b, dict)]
        if dt and blocks:
            parsed.append((dt, blocks))
    parsed.sort(key=lambda x: x[0])
    if not parsed:
        return Analysis([], {"window": None, "days_with_data": 0, "enough_data": False, "hints": [tx(lang, "no_data")]})

    end = parsed[-1][0]
    start7 = end - timedelta(days=6)
    workouts: list[_Workout] = []
    for dt, blocks in parsed:
        for b in blocks:
            if b.get("kind") == "workout":
                w = _read_workout(dt, b)
                if w:
                    workouts.append(w)

    sessions: list[_Session] = []
    for dt, blocks in parsed:
        for b in blocks:
            if b.get("kind") == "session":
                ss = _read_session(dt, b)
                if ss:
                    sessions.append(ss)
    start_prev = start7 - timedelta(days=7)
    wk_sessions = [x for x in sessions if x.day >= start7]
    prev_sessions = [x for x in sessions if start_prev <= x.day < start7]
    week_au = sum(x.load for x in wk_sessions)
    prev_au = sum(x.load for x in prev_sessions)

    week = [w for w in workouts if w.day >= start7]
    basis = "done" if sum(w.done for w in week) > 0 else "plan"
    sets_by: dict[str, int] = defaultdict(int)
    for w in week:
        if w.muscle:
            sets_by[w.muscle] += w.done if basis == "done" else w.planned
    total_sets = sum(w.done if basis == "done" else w.planned for w in week)
    push = sum(v for k, v in sets_by.items() if k in PUSH)
    pull = sum(v for k, v in sets_by.items() if k in PULL)
    enough = total_sets >= MIN_TOTAL_SETS
    basis_label = tx(lang, "basis_done" if basis == "done" else "basis_plan")

    stats: dict[str, Any] = {
        "window": {"start": start7.isoformat(), "end": end.isoformat()},
        "days_with_data": len(parsed), "basis": basis, "total_sets": total_sets, "enough_data": enough,
        "push_sets": push, "pull_sets": pull,
        "sets_by_muscle": {muscle_label(lang, k): sets_by.get(k, 0) for k in MUSCLE_LABEL},
        "session_load": {"count": len(wk_sessions), "minutes": round(sum(x.minutes for x in wk_sessions)),
                         "week_au": round(week_au), "prev_au": round(prev_au)},
        "hints": [],
    }
    found: list[dict] = []

    # 1) 통증/불편 메모
    texts = [(dt, _str(b.get("title"), 400).lower()) for dt, bs in parsed for b in bs if b.get("kind") == "text"]
    for region, (_ko_label, words, topic) in _REGIONS.items():
        label = REGION_LABELS[lang][region]
        for dt, t in reversed(texts):  # 가장 최근 언급 우선
            if any(w in t for w in words) and _PAIN.search(t) and not _NEGATION.search(t):
                found.append(_insight(
                    f"pain:{region}", "pain", "high", tx(lang, "pain_title", label=label),
                    tx(lang, "pain_detail", date=dt.isoformat(), label=label), [topic]))
                break

    # 2) 주간 운동량 / 밀기-당기기 균형
    if enough:
        imbalance = push >= MIN_WEEKLY_SETS and push > PUSH_PULL_RATIO * pull
        if imbalance:
            found.append(_insight(
                "push_pull", "push_pull", "medium", tx(lang, "pushpull_title"),
                tx(lang, "pushpull_detail", basis=basis_label, push=push, pull=pull, ratio=PUSH_PULL_RATIO), ["push_pull"],
                _suggest_block("back", MIN_WEEKLY_SETS - sets_by.get("back", 0), lang)))
        low = [g for g in MAJOR if sets_by.get(g, 0) < MIN_WEEKLY_SETS]
        order = {g: i for i, g in enumerate(MAJOR)}
        low.sort(key=lambda g: (sets_by.get(g, 0), 0 if (imbalance and g in PULL) else 1, order[g]))
        for g in low[:MAX_LOW_VOLUME]:
            n = sets_by.get(g, 0)
            found.append(_insight(
                f"low_volume:{g}", "low_volume", "medium" if n == 0 else "low",
                tx(lang, "lowvol_title", muscle=muscle_label(lang, g)),
                tx(lang, "lowvol_detail", basis=basis_label, muscle=muscle_label(lang, g), n=n, min=MIN_WEEKLY_SETS),
                ["rear_delt", "volume"] if g == "shoulders_rear" else ["volume"],
                _suggest_block(g, MIN_WEEKLY_SETS - n, lang)))
    else:
        stats["hints"].append(tx(lang, "hint_few_sets", n=MIN_TOTAL_SETS))

    # 3) 단백질 (체중이 있어야 g/kg 로 판단 가능)
    per_day: dict[date, float] = defaultdict(float)
    for dt, bs in parsed:
        for b in bs:
            if b.get("kind") == "meal" and b.get("eatenAt") not in (None, False, 0) and isinstance(b.get("plan"), dict):
                per_day[dt] += _num(b["plan"].get("proteinG"))
    days_p = [v for v in per_day.values() if v > 0]
    if weight_kg and len(days_p) >= MIN_PROTEIN_DAYS:
        avg = sum(days_p) / len(days_p)
        if avg / weight_kg < PROTEIN_G_PER_KG:
            found.append(_insight(
                "protein", "protein", "medium", tx(lang, "protein_title"),
                tx(lang, "protein_detail", days=len(days_p), avg=avg, gkg=avg / weight_kg, w=weight_kg, floor=PROTEIN_G_PER_KG),
                ["protein"]))
    elif not weight_kg:
        stats["hints"].append(tx(lang, "hint_weight"))
    elif len(days_p) < MIN_PROTEIN_DAYS:
        stats["hints"].append(tx(lang, "hint_protein_days", n=MIN_PROTEIN_DAYS))

    # 4) 정체기: 같은 운동의 세션별 볼륨이 최근 2회 동안 이전 최고를 넘지 못함
    by_ex: dict[str, dict[date, float]] = defaultdict(lambda: defaultdict(float))
    names: dict[str, str] = {}
    for w in workouts:
        if w.done > 0 and w.volume > 0:
            by_ex[w.key][w.day] += w.volume
            names[w.key] = w.title
    stalled = []
    for key, sessions in by_ex.items():
        vols = [v for _, v in sorted(sessions.items())]
        if len(vols) >= MIN_PLATEAU_SESSIONS and max(vols[-2:]) <= max(vols[:-2]):
            stalled.append((len(vols), key, max(vols[:-2]), max(vols[-2:])))
    for n, key, before, recent in sorted(stalled, reverse=True)[:MAX_PLATEAU]:
        found.append(_insight(
            f"plateau:{key}", "plateau", "low", tx(lang, "plateau_title", name=names[key]),
            tx(lang, "plateau_detail", name=names[key], n=n, before=before, recent=recent),
            ["plateau"]))

    # 5) 격투기/컨디셔닝 병행 (세션 블럭이 있으면 부하 수치도 함께 보여준다)
    names_all = [_norm(_str(b.get("title"), 80)) for _, bs in parsed for b in bs if b.get("kind") in ("workout", "text", "session")]
    combat = any(k in n for n in names_all for k in _COMBAT)
    cond = any(k in n for n in names_all for k in _CONDITIONING)
    if combat or cond:
        what = tx(lang, "what_combat" if combat else "what_cond")
        detail = tx(lang, "combat_detail", what=what)
        if wk_sessions:
            detail += tx(lang, "combat_sessions", n=len(wk_sessions),
                         m=round(sum(x.minutes for x in wk_sessions)), au=round(week_au))
        found.append(_insight("combat", "combat", "info", tx(lang, "combat_title", what=what), detail,
                              ["combat", "concurrent"] if combat else ["concurrent"]))

    # 6) 훈련 부하 급증: 최근 7일 부하가 직전 7일의 1.5배를 넘으면 (직전 부하가 충분할 때만)
    if prev_au >= LOAD_SPIKE_MIN_PREV_AU and week_au > prev_au * LOAD_SPIKE_RATIO:
        found.append(_insight(
            "load_spike", "load", "medium", tx(lang, "load_spike_title"),
            tx(lang, "load_spike_detail", prev=prev_au, cur=week_au, ratio=week_au / prev_au, limit=LOAD_SPIKE_RATIO),
            ["combat", "concurrent"]))

    # 7) 고강도 세션이 여러 날: RPE 8 이상 세션이 3일 이상이면 회복일 부족 신호
    hard_days = {x.day for x in wk_sessions if x.rpe >= HARD_RPE}
    if len(hard_days) >= HARD_DAYS_LIMIT:
        found.append(_insight(
            "hard_days", "load", "medium", tx(lang, "hard_days_title"),
            tx(lang, "hard_days_detail", n=len(hard_days), rpe=HARD_RPE, limit=HARD_DAYS_LIMIT),
            ["combat", "concurrent"]))

    found.sort(key=lambda i: _SEVERITY_RANK[i["severity"]])  # 안정 정렬: 같은 심각도 안에서는 발견 순서 유지
    return Analysis(found[:MAX_INSIGHTS], stats)

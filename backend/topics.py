"""추천 토픽 정의 — 논문 수집(PubMed 검색식)과 추천 시 검색 질의가 같은 곳을 바라보게 하는 단일 출처.

기록 분석(insights.py)이 만든 '약점/이슈'는 topic key 하나에 대응하고,
ingest_pubmed.py 는 같은 key 의 pubmed_term 으로 논문을 모은다.
따라서 새 이슈를 추가하려면 여기에 토픽을 먼저 추가하면 된다.

검색 질의(queries)는 논문 초록이 영어이므로 영어로 쓴다. 사용자의 한국어 메모는 검색에 쓰지 않는다.
"""
import re
from dataclasses import dataclass
from typing import Callable, Optional

from papers import Paper

Accept = Callable[[Paper], bool]


@dataclass(frozen=True)
class Topic:
    key: str
    title: str  # 사람이 읽는 이름 (수집 로그용)
    pubmed_term: str  # PubMed 검색식 (품질 필터는 pubmed_query() 가 덧붙인다)
    queries: tuple[str, ...]  # 추천 시 사용할 검색 질의
    # 필수 용어: 각 묶음에서 하나 이상이 제목+초록에 있어야 후보가 된다 (묶음끼리는 AND).
    # 소문자 영문/숫자/공백만 쓴다. 단어 전체로 맞추려면 앞뒤에 공백을 둔다 (" mma ").
    required: tuple[tuple[str, ...], ...] = ()
    # 제목에 있어야 하는 용어 묶음. 초록 한 줄에 스치듯 나오는 논문을 걸러낼 때 쓴다.
    required_title: tuple[tuple[str, ...], ...] = ()


# 일반 성인 운동인이 대상이므로, 제목에 아래 질환/집단이 있는 논문은 근거에서 뺀다.
# (예: 뇌졸중 환자의 어깨 전기자극 연구가 '후면 삼각근' 근거로 붙는 일을 막는다.) 제목 부분 문자열 일치.
OFF_POPULATION = (
    "stroke", "hemipleg", "covid", "parkinson", "cerebral palsy", "multiple sclerosis", "spinal cord",
    "dementia", "cancer", "hemodialysis", "dialysis", "heart failure", "copd",
)


# 근거 수준이 낮은 단일 연구보다 메타분석/체계적 문헌고찰/RCT/리뷰를 우선 수집한다.
QUALITY_FILTER = (
    'hasabstract[text] AND ("systematic review"[pt] OR "meta-analysis"[pt] '
    'OR "randomized controlled trial"[pt] OR "review"[pt])'
)

_T = [
    Topic(
        "volume",
        "주간 훈련 볼륨과 근비대",
        '("resistance training"[tiab] OR "strength training"[tiab]) AND '
        "(volume[tiab] OR sets[tiab]) AND hypertrophy[tiab]",
        ("weekly resistance training volume muscle hypertrophy dose response",),
    ),
    Topic(
        "rear_delt",
        "후면 삼각근 운동과 근활성도",
        '("rear deltoid"[tiab] OR "posterior deltoid"[tiab] OR "reverse fly"[tiab] OR "face pull"[tiab] '
        'OR "horizontal abduction"[tiab] OR "bent-over row"[tiab] OR "rear delt"[tiab]) '
        "AND (electromyography[tiab] OR EMG[tiab] OR activation[tiab] OR hypertrophy[tiab] OR strength[tiab])",
        (
            "rear deltoid posterior deltoid exercise electromyography activation",
            "horizontal abduction reverse fly face pull posterior shoulder muscle activation",
        ),
        # 'deltoid' 한 단어는 어깨 근전도 논문 대부분에 나오므로, 후면삼각근을 직접 가리키는 표현을 요구한다.
        (("posterior deltoid", "rear delt", "posterior delt", "deltoid posterior", "reverse fly", "reverse flye",
          "face pull", "horizontal abduction", "posterior portion", "posterior fib", "posterior head"),),
    ),
    Topic(
        "push_pull",
        "밀기/당기기 균형과 어깨",
        "((shoulder[tiab] AND (imbalance[tiab] OR scapular[tiab] OR pulling[tiab]) "
        'AND ("resistance training"[tiab] OR exercise[tiab])) '
        'OR "agonist-antagonist"[tiab] OR "push-pull"[tiab] OR "horizontal pulling"[tiab] '
        'OR ("muscle balance"[tiab] AND "resistance training"[tiab]))',
        (
            "pulling exercises rowing pulldown latissimus dorsi scapular muscle shoulder balance",
            "shoulder muscle imbalance pulling pushing resistance training scapular",
        ),
    ),
    Topic(
        "protein",
        "단백질 섭취와 근육",
        '(protein[tiab] AND (supplementation[tiab] OR intake[tiab]) AND "resistance training"[tiab])',
        ("dietary protein intake resistance training muscle mass gains",),
    ),
    Topic(
        "plateau",
        "정체기 / 점진적 과부하",
        '("progressive overload"[tiab] OR periodization[tiab] OR "training variation"[tiab]) '
        "AND (strength[tiab] OR hypertrophy[tiab])",
        ("progressive overload periodization strength hypertrophy progression",),
    ),
    Topic(
        "shoulder_pain",
        "어깨 충돌/통증과 운동",
        '("shoulder impingement"[tiab] OR subacromial[tiab]) AND (exercise[tiab] OR rehabilitation[tiab])',
        ("shoulder impingement exercise rehabilitation scapular",),
    ),
    Topic(
        "knee_pain",
        "무릎 통증과 운동",
        '("patellofemoral pain"[tiab] OR "knee pain"[tiab]) AND (exercise[tiab] OR "strength training"[tiab])',
        ("knee pain exercise strength training patellofemoral",),
    ),
    Topic(
        "low_back_pain",
        "허리 통증과 운동",
        '("low back pain"[tiab]) AND (exercise[tiab] OR "resistance training"[tiab])',
        ("low back pain exercise resistance training",),
    ),
    Topic(
        "combat",
        "격투기 컨디셔닝과 회복",
        '("combat sports"[tiab] OR MMA[tiab] OR "mixed martial arts"[tiab] OR boxing[tiab] OR judo[tiab] '
        'OR wrestling[tiab] OR "martial arts"[tiab] OR "jiu-jitsu"[tiab] OR taekwondo[tiab] OR karate[tiab] '
        'OR kickboxing[tiab] OR "muay thai"[tiab] OR grappling[tiab]) '
        "AND (conditioning[tiab] OR training[tiab] OR recovery[tiab] OR strength[tiab])",
        (
            "combat sports athletes strength conditioning training",
            "judo wrestling boxing martial arts training load recovery",
        ),
        (),
        (("combat", " boxing ", " boxer", " judo", "wrestl", "martial art", " mma ", "jiu jitsu", "taekwondo",
          " karate", "kickbox", "muay thai", "grappl", " fighter"),),
    ),
    Topic(
        "concurrent",
        "병행 훈련(근력+지구력)의 간섭 효과",
        '"concurrent training"[tiab] AND (strength[tiab] OR hypertrophy[tiab])',
        ("concurrent training endurance strength interference effect",),
        (("concurrent", "endurance", "aerobic"),),
    ),
]

TOPICS: dict[str, Topic] = {t.key: t for t in _T}


def pubmed_query(topic: Topic) -> str:
    return f"({topic.pubmed_term}) AND {QUALITY_FILTER}"


def queries_for(*keys: str) -> list[str]:
    """여러 토픽의 검색 질의를 순서대로 합친다 (중복 제거)."""
    out: list[str] = []
    for k in keys:
        for q in TOPICS[k].queries:
            if q not in out:
                out.append(q)
    return out


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _norm(text: str) -> str:
    return " " + _NON_ALNUM.sub(" ", text.lower()) + " "


def make_accept(topic: Topic) -> Accept:
    """논문이 이 토픽의 근거로 쓸 만한지 걸러내는 조건: 제외 집단 + 필수 용어."""

    def accept(p: Paper) -> bool:
        title = _norm(p.title)
        if any(w in title for w in OFF_POPULATION):
            return False
        if not all(any(w in title for w in group) for group in topic.required_title):
            return False
        if not topic.required:
            return True
        text = title + _norm(p.abstract)
        return all(any(w in text for w in group) for group in topic.required)

    return accept


def plan_for(*keys: str) -> list[tuple[str, Accept]]:
    """(검색 질의, 후보 조건) 목록. 질의는 토픽 순서대로 합치고 중복은 처음 것만 남긴다."""
    out: list[tuple[str, Accept]] = []
    seen: set[str] = set()
    for k in keys:
        acc = make_accept(TOPICS[k])
        for q in TOPICS[k].queries:
            if q not in seen:
                seen.add(q)
                out.append((q, acc))
    return out

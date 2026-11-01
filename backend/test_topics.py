# 토픽 후보 조건(필수 용어 / 제외 집단)과 질의 계획 테스트. 논문은 모두 직접 만든 가짜다.
import topics
from papers import Paper
from retrieval import Retriever


def P(pmid, title, abstract="", types=("Review",)):
    return Paper(pmid=pmid, title=title, abstract=abstract, conclusion="", journal="J", year=2020,
                 pub_types=list(types), authors="A", embedding=None)


def acc(key):
    return topics.make_accept(topics.TOPICS[key])


def test_off_population_titles_are_rejected_everywhere():
    stroke = P("1", "EMG-triggered stimulation for shoulder muscle activation in persons with stroke",
               "Posterior deltoid activation exercise.")
    covid = P("2", "Concurrent training for recovery from post-COVID-19 conditions", "concurrent training endurance")
    for key in topics.TOPICS:
        assert not acc(key)(stroke) and not acc(key)(covid)


def test_rear_delt_requires_rear_delt_wording_not_just_deltoid():
    ok = P("1", "Activation of the deltoid portions during exercises", "anterior, middle and posterior deltoid emg")
    face = P("2", "Face pull variations", "scapular muscles during the face pull")
    deltoid_only = P("3", "Postural correction and muscle activation", "emg of the upper trapezius and deltoid muscle")
    no = P("4", "Throwing exercise with TheraBand in volleyball players", "shoulder rotation deficit posterior capsule")
    assert acc("rear_delt")(ok) and acc("rear_delt")(face)
    assert not acc("rear_delt")(deltoid_only) and not acc("rear_delt")(no)


def test_combat_requires_a_combat_sport_word_in_the_title():
    judo = P("1", "Recovery in judo athletes", "training load")
    mma = P("2", "Conditioning for MMA fighters", "mma")
    velocity = P("3", "Improved strength and recovery after velocity-based training", "summary of comma gamma")
    passing_mention = P("4", "Block periodized training approaches for athletes", "examples include boxing and judo")
    assert acc("combat")(judo) and acc("combat")(mma) and not acc("combat")(velocity)  # 'mma' 는 단어로만 인정
    assert not acc("combat")(passing_mention)  # 초록에서 스치듯 언급만 한 논문은 제외


def test_topics_without_requirements_accept_anything_else():
    p = P("1", "Some resistance training study")
    assert acc("volume")(p) and acc("protein")(p)


def test_plan_for_merges_queries_and_keeps_each_topics_filter():
    plan = topics.plan_for("rear_delt", "volume", "rear_delt")
    qs = [q for q, _ in plan]
    assert len(qs) == len(set(qs)) and qs[0] == topics.TOPICS["rear_delt"].queries[0]
    assert qs[-1] == topics.TOPICS["volume"].queries[0] and len(plan) == len(topics.TOPICS["rear_delt"].queries) + 1
    vol = P("1", "Weekly volume", "resistance training")
    assert plan[0][1](vol) is False and plan[-1][1](vol) is True  # rear_delt 는 후면삼각근 표현 필요, volume 은 불필요


def test_every_topic_has_queries_and_a_valid_pubmed_term():
    for t in topics.TOPICS.values():
        assert t.queries and all(q.strip() for q in t.queries)
        q = topics.pubmed_query(t)
        assert q.count("(") == q.count(")") and q.count('"') % 2 == 0, t.key


def test_retriever_applies_accepts_per_query():
    a = P("1", "Rear deltoid exercise electromyography activation", "posterior deltoid exercise electromyography activation")
    b = P("2", "Shoulder exercise electromyography activation", "posterior shoulder exercise electromyography activation rear")
    r = Retriever([a, b])
    q = "rear deltoid posterior deltoid exercise electromyography activation"
    assert {p.pmid for p, _ in r.search([q], k=5, min_coverage=0.5)} == {"1", "2"}
    only_a = r.search([q], k=5, min_coverage=0.5, accepts=[acc("rear_delt")])
    assert [p.pmid for p, _ in only_a] == ["1"]

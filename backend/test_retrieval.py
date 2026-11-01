# 검색 테스트. 코퍼스는 검색 동작을 확인하려고 직접 만든 가짜 데이터이며 실제 논문이 아니다.
from papers import Paper
from retrieval import BM25Index, Retriever, tokenize


def P(pmid, title, abstract, types=("Review",), emb=None):
    return Paper(pmid=pmid, title=title, abstract=abstract, pub_types=list(types), embedding=emb)


VOL = P("1", "Resistance training volume and muscle hypertrophy",
        "We compared weekly sets of resistance training. Higher weekly volume produced greater muscle hypertrophy "
        "in a dose response manner.", ("Meta-Analysis",))
PROT = P("2", "Dietary protein supplementation and muscle mass",
         "Protein supplementation during resistance training increased lean mass.")
REAR = P("3", "Rear deltoid electromyography during reverse fly and face pull",
         "Posterior deltoid activation was highest in the reverse fly exercise.")
RICE = P("4", "Cooking temperature of rice", "Grain texture depends on water temperature.")
CORPUS = [VOL, PROT, REAR, RICE]


def pmids(res):
    return [p.pmid for p, _ in res]


def test_tokenize_stems_and_drops_stopwords():
    assert tokenize("The trained muscles") == tokenize("training muscle")
    assert tokenize("Exercises") == tokenize("exercise")
    assert tokenize("a of the and") == [] and tokenize("") == []


def test_ranks_relevant_first_and_gates_irrelevant():
    r = Retriever(CORPUS)
    assert pmids(r.search(["weekly resistance training volume muscle hypertrophy dose response"]))[0] == "1"
    got = pmids(r.search(["rear deltoid posterior deltoid exercise electromyography activation"], k=5))
    assert got == ["3"]  # 단어가 일부만 겹치는 논문(1, 2)과 무관한 논문(4)은 게이트에서 제외


def test_returns_nothing_when_corpus_has_no_match():
    r = Retriever(CORPUS)
    assert r.search(["quantum chromodynamics lattice simulation"]) == []
    assert r.search([""]) == [] and r.search([]) == []
    assert Retriever([]).search(["resistance training"]) == []


def test_coverage_threshold_is_adjustable():
    r = Retriever(CORPUS)
    # 7단어 중 4개만 일치한다. 일치하지 않은 3단어는 코퍼스에 없는 드문 단어라 가중치가 커서 커버리지는 약 35%다.
    q = "resistance training volume hypertrophy shoulder impingement rehabilitation"
    assert r.search([q]) == []                                  # 기본 60%: 제외
    assert pmids(r.search([q], min_coverage=0.3)) == ["1"]
    assert r.search([q], min_coverage=0.5) == [] and r.search([q], min_coverage=0.9) == []


def test_generic_shared_words_do_not_pass_the_gate():
    r = Retriever(CORPUS)
    # 단백질 논문은 'resistance training' 두 단어만 겹친다 (4단어 중 50%) -> 근거로 인용되면 안 됨
    assert pmids(r.search(["resistance training volume hypertrophy"], k=5)) == ["1"]


def test_multiple_queries_are_merged():
    r = Retriever(CORPUS)
    got = pmids(r.search(["resistance training volume hypertrophy", "reverse fly face pull deltoid"], k=5))
    assert set(got) == {"1", "3"}


def test_k_limits_results():
    docs = [P(str(i), "Resistance training study", "resistance training muscle") for i in range(10)]
    assert len(Retriever(docs).search(["resistance training muscle"], k=3)) == 3


def test_evidence_type_boost_breaks_ties():
    a = P("10", "Resistance training volume", "resistance training volume muscle", ("Journal Article",))
    b = P("11", "Resistance training volume", "resistance training volume muscle", ("Meta-Analysis",))
    assert pmids(Retriever([a, b]).search(["resistance training volume muscle"], k=2)) == ["11", "10"]


def test_embedding_reranks_candidates_only():
    same = "resistance training volume muscle hypertrophy"
    a = P("20", "Resistance training volume", same, emb=[1.0, 0.0])
    b = P("21", "Resistance training volume", same, emb=[0.0, 1.0])
    r = Retriever([a, b])
    assert pmids(r.search(["resistance training volume muscle"], k=2)) == ["20", "21"]  # 동점이면 입력 순서
    assert pmids(r.search(["resistance training volume muscle"], k=2, query_vectors=[[0.0, 5.0]])) == ["21", "20"]
    # 임베딩이 완벽히 일치해도 키워드 게이트를 통과하지 못하면 후보가 될 수 없다
    far = P("22", "Cooking rice", "grain texture", emb=[0.0, 1.0])
    assert "22" not in pmids(Retriever([a, b, far]).search(["resistance training volume muscle"], k=5,
                                                          query_vectors=[[0.0, 1.0]]))


def test_embedding_edge_cases_are_ignored_safely():
    same = "resistance training volume muscle"
    a = P("30", "Resistance training volume", same, emb=[1.0, 0.0])
    b = P("31", "Resistance training volume", same, emb=None)       # 임베딩 없는 논문
    c = P("32", "Resistance training volume", same, emb=[1.0, 0.0, 0.0])  # 차원이 다른 논문
    r = Retriever([a, b, c])
    out = pmids(r.search(["resistance training volume muscle"], k=5, query_vectors=[[1.0, 0.0]]))
    assert set(out) == {"30", "31", "32"} and out[0] == "30"
    assert len(r.search(["resistance training volume muscle"], query_vectors=[[0.0, 0.0]])) == 3  # 영벡터도 안전
    assert len(r.search(["resistance training volume muscle"], query_vectors=[])) == 3


def test_bm25_prefers_title_matches():
    a = P("40", "Face pull", "other words here entirely unrelated filler text")
    b = P("41", "Other topic", "face pull appears once in the abstract with filler text around it")
    res = BM25Index([a, b]).search("face pull")
    assert [i for i, _ in res][0] == 0


def test_query_weights_prefer_the_specific_query():
    r = Retriever(CORPUS)
    qs = ["weekly resistance training volume muscle hypertrophy dose response",
          "rear deltoid posterior deltoid exercise electromyography activation"]
    assert pmids(r.search(qs, k=2))[0] == "1"                      # 동일 가중치: 동점이면 입력 순서
    assert pmids(r.search(qs, k=2, weights=[1.0, 0.7]))[0] == "1"
    assert pmids(r.search(qs[::-1], k=2, weights=[1.0, 0.7]))[0] == "3"  # 구체적인 질의를 앞에 두면 그 논문이 먼저

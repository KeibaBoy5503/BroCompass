"""논문 검색: BM25 키워드 검색 + 관련도 게이트 + (선택) 임베딩 재순위. 표준 라이브러리만 사용한다.

설계 원칙
- 후보를 정하는 것은 키워드 검색(BM25)이다. 질의 단어의 일정 비율(min_coverage) 이상이 논문에 없으면
  점수가 높아도 후보에서 뺀다. 코퍼스에 맞는 논문이 없을 때 엉뚱한 논문이 근거로 인용되는 것을 막기 위해서다.
- 임베딩이 있으면 후보들의 순서만 다듬는다 (RRF 로 키워드 순위와 합침). 임베딩만으로 후보가 새로 생기지는 않는다.
"""
import math
import re
from collections import Counter
from typing import Callable, Optional

from papers import Paper

_STOP = frozenset(
    "a an and are as at be been by for from has have in into is it its of on or that the their this to "
    "was were with within using use used effect effects study studies between during after among".split()
)
_WORD = re.compile(r"[a-z0-9]+")

# 질의 단어의 이 비율 이상이 논문(제목+초록)에 있어야 후보가 된다. 짧은 질의에서 일반 단어만 겹치는 논문을 거른다.
# 비율은 단어의 희귀도(IDF)로 가중한다: 'training', 'strength' 같은 흔한 단어보다 'antagonist', 'deltoid' 같은 드문 단어가 더 크게 센다.
DEFAULT_MIN_COVERAGE = 0.6
# 질의 안에서 1위 점수의 이 비율에 못 미치는 논문은 후보에서 뺀다. 맞는 논문이 적은 주제에서 억지로 3편을 채우지 않기 위해서다.
DEFAULT_MIN_REL_SCORE = 0.4


def _stem(w: str) -> str:
    """아주 단순한 어미 제거. 질의와 문서에 같은 규칙을 적용하므로 일관되게만 동작하면 된다."""
    for suf, rep in (("ies", "y"), ("sses", "ss"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            w = w[: len(w) - len(suf)] + rep
            break
    if w.endswith("e") and len(w) > 4:
        w = w[:-1]
    return w


def tokenize(text: str) -> list[str]:
    return [_stem(w) for w in _WORD.findall(text.lower()) if len(w) > 1 and w not in _STOP]


def _type_boost(pub_types: list[str]) -> float:
    """근거 수준이 높은 연구 유형에 약한 가산점. 키워드 관련도를 뒤집을 만큼 크지는 않다."""
    types = {t.lower() for t in pub_types}
    if types & {"meta-analysis", "systematic review"}:
        return 1.15
    if "randomized controlled trial" in types:
        return 1.05
    return 1.0


class BM25Index:
    def __init__(self, papers: list[Paper], k1: float = 1.5, b: float = 0.75):
        self.papers, self.k1, self.b = papers, k1, b
        self._tf: list[Counter] = []
        self._len: list[int] = []
        df: Counter = Counter()
        for p in papers:
            toks = tokenize(p.title) * 2 + tokenize(p.abstract)  # 제목을 두 번 세어 가중
            c = Counter(toks)
            self._tf.append(c)
            self._len.append(len(toks))
            df.update(c.keys())
        n = len(papers)
        self._avg = (sum(self._len) / n) if n else 1.0
        self._idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def search(
        self,
        query: str,
        limit: int = 30,
        min_coverage: float = DEFAULT_MIN_COVERAGE,
        accept: Optional[Callable[[Paper], bool]] = None,
        min_rel_score: float = 0.0,
    ) -> list[tuple[int, float]]:
        """(논문 인덱스, 점수) 목록, 점수 내림차순. 관련도 게이트와 accept 조건을 통과한 것만 반환한다.
        min_rel_score > 0 이면 1위 점수의 그 비율에 못 미치는 논문도 뺀다."""
        qt = list(dict.fromkeys(tokenize(query)))
        if not qt:
            return []
        unseen = math.log(1 + (len(self.papers) + 0.5) / 0.5)  # 코퍼스에 한 번도 없는 단어는 가장 희귀한 단어로 센다
        weight = {t: self._idf.get(t, unseen) for t in qt}
        total_w = sum(weight.values())
        out = []
        for i, tf in enumerate(self._tf):
            hits = [t for t in qt if t in tf]
            if sum(weight[t] for t in hits) / total_w < min_coverage:
                continue
            if accept is not None and not accept(self.papers[i]):
                continue
            norm = self.k1 * (1 - self.b + self.b * self._len[i] / self._avg)
            score = sum(self._idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + norm) for t in hits)
            out.append((i, score * _type_boost(self.papers[i].pub_types)))
        out.sort(key=lambda x: (-x[1], x[0]))
        if min_rel_score > 0 and out:
            floor = out[0][1] * min_rel_score
            out = [x for x in out if x[1] >= floor]
        return out[:limit]


def _ranks(scored: list[tuple[int, float]]) -> dict[int, int]:
    """점수 내림차순 목록 -> 인덱스별 순위. 동점은 같은 순위를 받는다 (임의의 입력 순서가 순위를 가르지 않도록)."""
    ranks: dict[int, int] = {}
    prev: Optional[float] = None
    rank = 0
    for pos, (i, s) in enumerate(scored):
        if prev is None or abs(s - prev) > 1e-9:
            rank = pos
        ranks[i] = rank
        prev = s
    return ranks


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _unit(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n > 0 else v


class Retriever:
    RRF_K = 60

    def __init__(self, papers: list[Paper]):
        self.papers = papers
        self._bm25 = BM25Index(papers)

    def search(
        self,
        queries: list[str],
        k: int = 3,
        query_vectors: Optional[list[list[float]]] = None,
        min_coverage: float = DEFAULT_MIN_COVERAGE,
        pool: int = 30,
        weights: Optional[list[float]] = None,
        accepts: Optional[list[Optional[Callable[[Paper], bool]]]] = None,
        min_rel_score: float = DEFAULT_MIN_REL_SCORE,
    ) -> list[tuple[Paper, float]]:
        """여러 질의의 결과를 RRF 로 합쳐 상위 k 편을 돌려준다.

        query_vectors[i] 는 queries[i] 의 임베딩. weights[i] 는 queries[i] 의 가중치(기본 1.0)로,
        '구체적인 질의'에 더 큰 값을 주면 일반적인 질의에만 걸린 논문보다 위에 놓인다.
        accepts[i] 는 queries[i] 의 후보 조건(필수 용어, 제외 집단 등). 조건은 질의별로 따로 적용된다.
        min_rel_score 는 질의별 1위 BM25 점수 대비 최소 비율 (0 이면 사용 안 함).
        """
        total: dict[int, float] = {}
        for qi, q in enumerate(queries):
            acc = accepts[qi] if accepts and qi < len(accepts) else None
            lex = self._bm25.search(q, pool, min_coverage, acc, min_rel_score)
            if not lex:
                continue
            rankings = [_ranks(lex)]
            if query_vectors and qi < len(query_vectors):
                qv = _unit(query_vectors[qi])
                dense = [
                    (i, _dot(qv, self.papers[i].embedding))
                    for i, _ in lex
                    if self.papers[i].embedding and len(self.papers[i].embedding) == len(qv)
                ]
                dense.sort(key=lambda x: (-x[1], x[0]))
                if dense:
                    rankings.append(_ranks(dense))
            w = weights[qi] if weights and qi < len(weights) else 1.0
            for ranking in rankings:
                for i, rank in ranking.items():
                    total[i] = total.get(i, 0.0) + w / (self.RRF_K + rank + 1)
        ordered = sorted(total.items(), key=lambda x: (-x[1], x[0]))[:k]
        return [(self.papers[i], s) for i, s in ordered]

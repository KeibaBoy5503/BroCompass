"""논문 검색 품질 점검 도구 (내 PC에서 실행, 네트워크·API 키 불필요).

각 추천 항목(인사이트)에 어떤 논문이 붙는지 보여준다. 결과를 복사해서 공유하면 검색식/기준을 조정할 수 있다.

    python eval_retrieval.py                 # 모든 항목
    python eval_retrieval.py --topic rear_delt,volume
    python eval_retrieval.py --db other.db --k 5 --min-coverage 0.5 --min-rel 0.5
    python eval_retrieval.py --debug         # 질의별 후보와 BM25 점수까지 출력 (기준을 조정할 때)
    python eval_retrieval.py > report.txt
"""
import argparse
import os
import sys

from papers import PaperStore
from retrieval import DEFAULT_MIN_COVERAGE, DEFAULT_MIN_REL_SCORE, Retriever
from topics import OFF_POPULATION, TOPICS, make_accept, plan_for

# insights.py 가 실제로 만드는 항목과 같은 토픽 조합
CASES = {
    "밀기/당기기 불균형": ["push_pull"],
    "등 운동량 부족": ["volume"],
    "후면삼각근 운동량 부족": ["rear_delt", "volume"],
    "단백질 부족": ["protein"],
    "정체기": ["plateau"],
    "어깨 통증 메모": ["shoulder_pain"],
    "무릎 통증 메모": ["knee_pain"],
    "허리 통증 메모": ["low_back_pain"],
    "격투기 병행": ["combat", "concurrent"],
    "유산소만 병행": ["concurrent"],
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=os.environ.get("BROCOMPASS_PAPERS_DB", os.path.join(os.path.dirname(__file__), "papers.db")))
    ap.add_argument("--topic", help="쉼표로 구분한 토픽 키 하나의 조합만 점검 (예: rear_delt,volume)")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--min-coverage", type=float, default=DEFAULT_MIN_COVERAGE)
    ap.add_argument("--min-rel", type=float, default=DEFAULT_MIN_REL_SCORE, help="질의별 1위 점수 대비 최소 비율 (0=끔)")
    ap.add_argument("--debug", action="store_true", help="질의별 BM25 후보(상위 8)와 점수를 함께 출력")
    args = ap.parse_args()

    papers = PaperStore(args.db).all()
    print(f"논문 DB: {args.db} ({len(papers)}편)\n")
    if not papers:
        print("논문이 없습니다. 먼저 python ingest_pubmed.py 를 실행하세요.")
        return 1

    off = [p for p in papers if any(w in p.title.lower() for w in OFF_POPULATION)]
    print(f"제목에 제외 집단(뇌졸중·코로나 등)이 있어 근거에서 빼는 논문: {len(off)}편\n")

    cases = {"직접 지정": args.topic.split(",")} if args.topic else CASES
    for name, keys in cases.items():
        bad = [k for k in keys if k not in TOPICS]
        if bad:
            print(f"알 수 없는 토픽: {bad} (가능: {', '.join(TOPICS)})")
            return 2
        plan = plan_for(*keys)
        qs = [q for q, _ in plan]
        passing = sum(1 for p in papers if any(a(p) for _, a in plan))
        retriever = Retriever(papers)
        found = retriever.search(
            qs, k=args.k, min_coverage=args.min_coverage, min_rel_score=args.min_rel,
            accepts=[a for _, a in plan], weights=[1.0] + [0.7] * (len(qs) - 1),
        )
        print(f"== {name}  [{', '.join(keys)}]  (조건 통과 논문 {passing}편)")
        if args.debug:
            for q, a in plan:
                cands = retriever._bm25.search(q, 8, args.min_coverage, a, args.min_rel)
                print(f"   [질의] {q}  (후보 {len(cands)}편)")
                for i, sc in cands:
                    print(f"      bm25 {sc:6.2f}  {papers[i].title[:90]}")
        if not found:
            print("   (붙는 논문 없음 -> 화면에는 '근거 없음'으로 표시)")
        for p, s in found:
            print(f"   - {p.title[:110]}")
            print(f"     {p.year} · {', '.join(p.pub_types[:3])} · PMID {p.pmid} · 점수 {s:.4f}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())

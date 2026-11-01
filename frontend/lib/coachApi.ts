export type Severity = "high" | "medium" | "low" | "info";

export type PaperView = {
  pmid: string;
  title: string;
  journal: string;
  year: number | null;
  doi: string;
  pub_types: string[];
  authors: string;
  snippet: string;
};

export type SuggestedBlock = { title: string; sets: number; reps: number; weightKg: number };
export type Advice = { summary: string; suggestion: string; pmids: string[] };

export type Insight = {
  id: string;
  kind: string;
  severity: Severity;
  title: string;
  detail: string;
  topics: string[];
  suggested_blocks: SuggestedBlock[];
  papers: PaperView[];
  advice: Advice | null;
  /** AI 가 이 항목과 관련이 낮다고 판단해 숨긴 논문 수 (AI 요약을 쓴 경우에만 있다) */
  hidden_papers?: number;
};

export type CoachStats = {
  window: { start: string; end: string } | null;
  days_with_data: number;
  enough_data: boolean;
  basis?: "done" | "plan";
  total_sets?: number;
  push_sets?: number;
  pull_sets?: number;
  sets_by_muscle?: Record<string, number>;
  hints: string[];
};

export type CoachResult = {
  stats: CoachStats;
  insights: Insight[];
  papers_in_db: number;
  retrieval: "keyword" | "hybrid";
  generated: boolean;
  model: string | null;
  llm_error: string | null;
  disclaimer: string;
};

export type PaperStats = {
  count: number;
  last_fetched: number | null;
  embedded: number;
  llm_configured: boolean;
  embeddings_enabled: boolean;
};

const TIMEOUT_MS = 100_000; // 서버의 AI 호출(최대 60초)보다 조금 길게

async function errorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const j = await res.json();
    if (typeof j?.detail === "string") return j.detail; // 검증 오류(422)는 배열이라 건너뜀
  } catch {
    /* 본문이 JSON 이 아님 */
  }
  return `${fallback} (${res.status})`;
}

export async function fetchPaperStats(): Promise<PaperStats> {
  const res = await fetch("/api/papers/stats");
  if (!res.ok) throw new Error(await errorMessage(res, "논문 DB 상태를 불러오지 못했어요"));
  return res.json();
}

export async function fetchRecommendation(
  days: { date: string; blocks: unknown[] }[],
  weightKg: number | undefined,
  useLlm: boolean,
  lang: "ko" | "ja" | "en" = "ko"
): Promise<CoachResult> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res: Response;
  try {
    res = await fetch("/api/coach/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ days, weight_kg: weightKg, use_llm: useLlm, lang }),
      signal: ctrl.signal,
    });
  } catch {
    throw new Error("서버에 연결하지 못했어요. 백엔드가 켜져 있는지 확인해 주세요.");
  } finally {
    clearTimeout(timer);
  }
  if (!res.ok) throw new Error(await errorMessage(res, "추천을 불러오지 못했어요"));
  return res.json();
}

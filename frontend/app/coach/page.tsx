"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import InsightCard from "@/components/coach/InsightCard";
import Logo from "@/components/Logo";
import {
  fetchPaperStats,
  fetchRecommendation,
  type CoachResult,
  type PaperStats,
  type SuggestedBlock,
} from "@/lib/coachApi";
import { buildDays, suggestionToBlock } from "@/lib/coachPayload";
import { todayStr } from "@/lib/date";
import { haptic } from "@/lib/haptic";
import { useDailyNote } from "@/lib/useDailyNote";
import { useLang } from "@/lib/i18n";

const PERIODS = [7, 14, 28] as const;
const WEIGHT_KEY = "brocompass:weight";

export default function CoachPage() {
  // 서버와 클라이언트의 '오늘'이 달라 hydration 불일치가 나지 않도록 마운트 후 결정한다.
  const [date, setDate] = useState<string | null>(null);
  useEffect(() => setDate(todayStr()), []);
  if (!date) return <main className="min-h-screen" />;
  return <CoachBody date={date} />;
}

const LOCALE = { ko: "ko-KR", ja: "ja-JP", en: "en-US" } as const;

function CoachBody({ date }: { date: string }) {
  const { t, lang } = useLang();
  const { addBlock } = useDailyNote(date); // 추천된 운동을 '오늘' 노트에 추가하기 위해 사용
  const [period, setPeriod] = useState<(typeof PERIODS)[number]>(14);
  const [weight, setWeight] = useState("");
  const [useLlm, setUseLlm] = useState(true);
  const [stats, setStats] = useState<PaperStats | null>(null);
  const [statsError, setStatsError] = useState(false);
  const [result, setResult] = useState<CoachResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      setWeight(localStorage.getItem(WEIGHT_KEY) ?? "");
    } catch {
      /* 저장소 차단 */
    }
    fetchPaperStats().then(setStats).catch(() => setStatsError(true));
  }, []);

  const weightKg = (() => {
    const n = Number(weight);
    return Number.isFinite(n) && n >= 30 && n <= 300 ? n : undefined;
  })();

  const run = async () => {
    setError(null);
    const days = buildDays(date, period);
    if (days.length === 0) {
      setError(t("최근 {n}일 안에 이 기기에 저장된 기록이 없어요. 데일리 노트를 먼저 기록해 주세요.", { n: period }));
      return;
    }
    try {
      localStorage.setItem(WEIGHT_KEY, weight);
    } catch {
      /* ignore */
    }
    haptic(15);
    setLoading(true);
    try {
      setResult(await fetchRecommendation(days, weightKg, useLlm, lang));
      haptic([20, 30, 40]);
    } catch (e) {
      setError(t(e instanceof Error ? e.message : "알 수 없는 오류가 발생했어요."));
    } finally {
      setLoading(false);
    }
  };

  const addSuggestion = (s: SuggestedBlock) => addBlock(suggestionToBlock(s));
  const emptyDb = stats !== null && stats.count === 0;

  return (
    <main className="mx-auto max-w-md space-y-5 px-4 pb-24 pt-8 md:max-w-2xl lg:max-w-3xl">
      <header className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Logo size={36} />
          <div>
            <h1 className="text-lg font-bold tracking-tight">
              Evidence <span className="text-neon">Coach</span>
            </h1>
            <p className="font-mono text-xs text-zinc-500">{t("내 기록 × PubMed 논문")}</p>
          </div>
        </div>
        <Link href="/note" className="font-mono text-xs text-zinc-500 hover:text-neon">
          {t("← 노트")}
        </Link>
      </header>

      {statsError && (
        <p role="alert" className="rounded-xl border border-red-400/30 bg-red-400/5 p-3 font-mono text-xs text-red-300">
          {t("서버에 연결하지 못했어요. 백엔드(uvicorn)가 켜져 있는지 확인해 주세요.")}
        </p>
      )}
      {emptyDb && (
        <div className="rounded-xl border border-amber-400/30 bg-amber-400/5 p-3 text-xs leading-relaxed text-amber-200">
          <p className="font-semibold">{t("논문 DB가 비어 있어요.")}</p>
          <p className="mt-1 text-amber-200/80">
            {t("분석은 되지만 근거 논문은 표시되지 않아요. 백엔드 폴더에서 아래 명령으로 논문을 수집하세요.")}
          </p>
          <code className="mt-2 block rounded-lg bg-ink px-3 py-2 font-mono text-[11px] text-zinc-300">
            python ingest_pubmed.py --email you@example.com
          </code>
        </div>
      )}
      {stats && stats.count > 0 && (
        <p className="font-mono text-[11px] text-zinc-600">
          {t("논문 DB {n}편", { n: stats.count })}
          {stats.last_fetched ? t(" · 최근 수집 {d}", { d: new Date(stats.last_fetched * 1000).toLocaleDateString(LOCALE[lang]) }) : ""}
          {stats.embeddings_enabled && stats.embedded > 0 ? t(" · 임베딩 사용") : ""}
        </p>
      )}

      <section className="space-y-4 rounded-2xl border border-line bg-panel p-4">
        <div>
          <span className="mb-1.5 block font-mono text-xs uppercase tracking-wider text-zinc-500">{t("분석 기간")}</span>
          <div className="grid grid-cols-3 gap-2">
            {PERIODS.map((p) => (
              <motion.button
                key={p}
                type="button"
                whileTap={{ scale: 0.94 }}
                onClick={() => {
                  haptic(10);
                  setPeriod(p);
                }}
                className={`rounded-lg border py-3 text-sm transition ${
                  period === p ? "border-neon bg-neon/10 text-neon shadow-neon" : "border-line bg-ink text-zinc-400"
                }`}
              >
                {t("최근 {n}일", { n: p })}
              </motion.button>
            ))}
          </div>
        </div>

        <label className="block">
          <span className="mb-1.5 block font-mono text-xs uppercase tracking-wider text-zinc-500">
            {t("체중 kg (선택 · 단백질 분석용)")}
          </span>
          <input
            inputMode="decimal"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            placeholder={t("예: 75")}
            className="w-full rounded-lg border border-line bg-ink px-3 py-3 text-zinc-100 outline-none focus:border-neon"
          />
        </label>

        <label className="flex items-center gap-2 text-sm text-zinc-300">
          <input
            type="checkbox"
            checked={useLlm}
            onChange={(e) => setUseLlm(e.target.checked)}
            className="h-4 w-4 accent-[#39FF88]"
          />
          {t("AI로 논문 근거 요약하기")}
          {stats && !stats.llm_configured && <span className="text-xs text-zinc-600">{t("(서버에 API 키 없음)")}</span>}
        </label>

        <motion.button
          type="button"
          whileTap={{ scale: 0.97 }}
          disabled={loading}
          onClick={run}
          className="w-full rounded-lg bg-neon py-4 font-bold text-black shadow-neon disabled:opacity-50"
        >
          {loading ? t("분석하는 중…") : t("내 기록 분석하기")}
        </motion.button>
        <p className="text-[11px] leading-relaxed text-zinc-600">
          {t("이 기기에 저장된 기록이 내 서버로 전송돼요. AI에는 분석 결과와 논문 발췌만 보내고 메모 원문은 보내지 않아요.")}
        </p>
      </section>

      {error && (
        <p role="alert" className="rounded-xl border border-red-400/30 bg-red-400/5 p-3 text-sm text-red-300">
          {error}
        </p>
      )}

      {result && (
        <section className="space-y-4" aria-live="polite">
          {result.stats.window && (
            <p className="font-mono text-xs text-zinc-500">
              {t("기록 {d}일 · 최근 7일({s} ~ {e}) {basis} {n}세트", { d: result.stats.days_with_data, s: result.stats.window.start, e: result.stats.window.end, basis: t(result.stats.basis === "plan" ? "계획" : "완료"), n: result.stats.total_sets ?? 0 })}
              {result.retrieval === "hybrid" ? t(" · 하이브리드 검색") : ""}
            </p>
          )}
          {result.stats.hints.map((h) => (
            <p key={h} className="rounded-lg border border-line bg-panel px-3 py-2 text-xs text-zinc-400">
              💡 {h}
            </p>
          ))}
          {result.llm_error && (
            <p className="rounded-lg border border-amber-400/30 bg-amber-400/5 px-3 py-2 text-xs text-amber-200">
              {t("AI 요약을 만들지 못했어요: {err}", { err: result.llm_error })}
            </p>
          )}

          {result.insights.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-line p-8 text-center text-sm text-zinc-500">
              {t("지금 기록에서는 특별히 짚을 점이 보이지 않아요. 👍")}
            </div>
          ) : (
            result.insights.map((i) => <InsightCard key={i.id} insight={i} onAddBlock={addSuggestion} />)
          )}

          <p className="text-[11px] leading-relaxed text-zinc-600">{result.disclaimer}</p>
        </section>
      )}
    </main>
  );
}

"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import type { Insight, PaperView, Severity } from "@/lib/coachApi";
import { doiUrl, pubmedUrl } from "@/lib/coachPayload";
import { haptic } from "@/lib/haptic";
import type { SuggestedBlock } from "@/lib/coachApi";
import { useT } from "@/lib/i18n";

const SEVERITY: Record<Severity, { label: string; chip: string }> = {
  high: { label: "주의", chip: "border-red-400/50 bg-red-400/10 text-red-300" },
  medium: { label: "확인", chip: "border-amber-400/50 bg-amber-400/10 text-amber-300" },
  low: { label: "참고", chip: "border-sky-400/50 bg-sky-400/10 text-sky-300" },
  info: { label: "정보", chip: "border-line bg-ink text-zinc-400" },
};

function Paper({ p, cited }: { p: PaperView; cited: boolean }) {
  const t = useT();
  const [open, setOpen] = useState(false);
  const pm = pubmedUrl(p.pmid);
  const doi = doiUrl(p.doi);
  return (
    <li className={`rounded-xl border p-3 ${cited ? "border-neon/40 bg-neon/5" : "border-line bg-ink"}`}>
      <p className="text-sm font-medium leading-snug text-zinc-100">{p.title}</p>
      <p className="mt-1 font-mono text-[11px] text-zinc-500">
        {[p.authors, p.journal, p.year].filter(Boolean).join(" · ")}
      </p>
      {p.pub_types.length > 0 && (
        <div className="mt-1.5 flex flex-wrap gap-1">
          {p.pub_types.slice(0, 3).map((pt) => (
            <span key={pt} className="rounded-full border border-line px-2 py-0.5 font-mono text-[10px] text-zinc-500">
              {pt}
            </span>
          ))}
          {cited && (
            <span className="rounded-full border border-neon/40 px-2 py-0.5 font-mono text-[10px] text-neon">
              {t("AI 요약이 인용")}
            </span>
          )}
        </div>
      )}
      {p.snippet && (
        <>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            className="mt-2 font-mono text-[11px] text-zinc-500 hover:text-neon"
          >
            {open ? t("▲ 발췌 접기") : t("▼ 결론/초록 발췌 보기")}
          </button>
          {open && <p className="mt-1 text-xs leading-relaxed text-zinc-400">{p.snippet}</p>}
        </>
      )}
      <div className="mt-2 flex gap-3 font-mono text-[11px]">
        {pm && (
          <a href={pm} target="_blank" rel="noopener noreferrer" className="text-neon hover:underline">
            PubMed {p.pmid} ↗
          </a>
        )}
        {doi && (
          <a href={doi} target="_blank" rel="noopener noreferrer" className="text-zinc-500 hover:text-neon">
            DOI ↗
          </a>
        )}
      </div>
    </li>
  );
}

export default function InsightCard({
  insight,
  onAddBlock,
}: {
  insight: Insight;
  onAddBlock: (s: SuggestedBlock) => void;
}) {
  const t = useT();
  const sev = SEVERITY[insight.severity] ?? SEVERITY.info;
  const [added, setAdded] = useState<Set<number>>(new Set());
  const cited = new Set(insight.advice?.pmids ?? []);

  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-3 rounded-2xl border border-line bg-panel p-4"
    >
      <header className="flex items-start gap-2">
        <span className={`mt-0.5 shrink-0 rounded-full border px-2 py-0.5 font-mono text-[10px] ${sev.chip}`}>
          {t(sev.label)}
        </span>
        <h3 className="font-semibold leading-snug">{insight.title}</h3>
      </header>
      <p className="text-sm leading-relaxed text-zinc-400">{insight.detail}</p>

      {insight.advice && (
        <div className="rounded-xl border border-neon/30 bg-neon/5 p-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-neon">{t("AI 요약 · 원문 확인 필요")}</p>
          <p className="mt-1.5 text-sm leading-relaxed text-zinc-100">{insight.advice.summary}</p>
          {insight.advice.suggestion && (
            <p className="mt-1.5 text-sm leading-relaxed text-zinc-300">→ {insight.advice.suggestion}</p>
          )}
        </div>
      )}

      {insight.suggested_blocks.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {insight.suggested_blocks.map((s, i) => (
            <motion.button
              key={i}
              type="button"
              whileTap={{ scale: 0.95 }}
              disabled={added.has(i)}
              onClick={() => {
                haptic([20, 30, 20]);
                onAddBlock(s);
                setAdded((prev) => new Set(prev).add(i));
              }}
              className="rounded-lg border border-neon/50 bg-neon/10 px-3 py-2 font-mono text-xs text-neon disabled:opacity-50"
            >
              {added.has(i) ? t("✓ 오늘 노트에 추가됨") : t("＋ {title} {sets}×{reps} 오늘 노트에 추가", { title: s.title, sets: s.sets, reps: s.reps })}
            </motion.button>
          ))}
        </div>
      )}

      {insight.papers.length > 0 ? (
        <div>
          <p className="mb-2 font-mono text-[10px] uppercase tracking-widest text-zinc-500">
            {t("관련 논문 {n}편", { n: insight.papers.length })}
          </p>
          <ul className="space-y-2">
            {insight.papers.map((p) => (
              <Paper key={p.pmid} p={p} cited={cited.has(p.pmid)} />
            ))}
          </ul>
          {!!insight.hidden_papers && (
            <p className="mt-2 font-mono text-[10px] text-zinc-600">
              {t("AI가 관련성이 낮다고 판단해 {n}편을 숨겼어요.", { n: insight.hidden_papers })}
            </p>
          )}
        </div>
      ) : (
        <p className="font-mono text-[11px] text-zinc-600">
          {insight.hidden_papers
            ? t("검색된 논문 {n}편을 AI가 관련성이 낮다고 판단해 숨겼어요. 근거가 부족한 주제예요.", { n: insight.hidden_papers })
            : t("논문 DB에서 이 주제와 충분히 관련된 논문을 찾지 못했어요.")}
        </p>
      )}
    </motion.article>
  );
}

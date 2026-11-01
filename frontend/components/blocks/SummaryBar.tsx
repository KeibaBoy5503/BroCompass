"use client";

import { motion } from "framer-motion";
import { useT } from "@/lib/i18n";
import { pct, type Summary } from "@/lib/summary";

function Row({
  label,
  done,
  planned,
  unit,
  color,
}: {
  label: string;
  done: number;
  planned: number;
  unit: string;
  color: string;
}) {
  const t = useT();
  const p = pct(done, planned);
  return (
    <div>
      <div className="mb-1 flex justify-between font-mono text-xs">
        <span className="text-zinc-500">{t(label)}</span>
        <span className="text-zinc-300">
          {Math.round(done)} / {Math.round(planned)} {t(unit)}
          <span className="ml-2 text-zinc-500">{p}%</span>
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-line">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 8px ${color}` }}
          initial={false}
          animate={{ width: `${p}%` }}
          transition={{ type: "spring", stiffness: 120, damping: 20 }}
        />
      </div>
    </div>
  );
}

export default function SummaryBar({ summary }: { summary: Summary }) {
  const hasWorkout = summary.plannedSets > 0;
  const hasMeal = summary.plannedKcal > 0;
  const hasSession = summary.plannedLoad > 0;
  if (!hasWorkout && !hasMeal && !hasSession) return null;

  return (
    <section className="space-y-3 rounded-2xl border border-line bg-panel p-4">
      <h2 className="font-mono text-xs uppercase tracking-widest text-zinc-500">
        PLAN vs ACTUAL
      </h2>
      {hasWorkout && (
        <>
          <Row label="세트" done={summary.doneSets} planned={summary.plannedSets} unit="세트" color="#39FF88" />
          <Row label="볼륨" done={summary.volumeDone} planned={summary.volumePlanned} unit="kg" color="#A78BFA" />
        </>
      )}
      {hasSession && (
        <Row label="세션 부하" done={summary.doneLoad} planned={summary.plannedLoad} unit="AU" color="#FB7185" />
      )}
      {hasMeal && (
        <>
          <Row label="칼로리" done={summary.eatenKcal} planned={summary.plannedKcal} unit="kcal" color="#FBBF24" />
          <Row label="단백질" done={summary.eatenProteinG} planned={summary.plannedProteinG} unit="g" color="#38BDF8" />
        </>
      )}
    </section>
  );
}

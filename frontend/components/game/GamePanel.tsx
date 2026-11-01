"use client";

import { motion } from "framer-motion";
import { useT } from "@/lib/i18n";
import type { GameState, Quest } from "@/lib/game";

const bar = (ratio: number, color: string) => (
  <div className="h-1.5 overflow-hidden rounded-full bg-line">
    <motion.div
      className="h-full rounded-full"
      style={{ background: color, boxShadow: `0 0 8px ${color}` }}
      initial={false}
      animate={{ width: `${Math.min(Math.max(ratio, 0), 1) * 100}%` }}
      transition={{ type: "spring", stiffness: 120, damping: 20 }}
    />
  </div>
);

function QuestRow({ q }: { q: Quest }) {
  const t = useT();
  return (
    <li className="space-y-1.5">
      <div className="flex items-center justify-between gap-2 font-mono text-xs">
        <span className={q.complete ? "text-neon" : "text-zinc-300"}>
          {q.complete ? "✓ " : ""}
          {t(q.label)}
        </span>
        <span className="shrink-0 text-zinc-500">
          {Math.min(q.done, q.target)}/{q.target}
          {t(q.unit)}
        </span>
      </div>
      {bar(q.done / q.target, q.complete ? "#39FF88" : "#A78BFA")}
    </li>
  );
}

export default function GamePanel({ state }: { state: GameState }) {
  const t = useT();
  const { level, streak, quests, weekPRs } = state;
  const doneCount = quests.filter((q) => q.complete).length;

  return (
    <section className="space-y-5 rounded-2xl border border-line bg-panel p-4">
      <div>
        <div className="mb-1.5 flex items-baseline justify-between font-mono">
          <span className="text-sm font-bold text-neon">Lv.{level.level}</span>
          <span className="text-xs text-zinc-500">
            {level.into} / {level.need} XP
          </span>
        </div>
        {bar(level.into / level.need, "#39FF88")}
      </div>

      <div className="flex items-center justify-between rounded-xl border border-line bg-ink px-3 py-2.5">
        <div className="font-mono">
          <div className="text-xs text-zinc-500">{t("연속 운동")}</div>
          <div className="text-lg font-bold text-zinc-100">
            {streak.current > 0 ? "🔥 " : ""}
            {streak.current}
            <span className="ml-1 text-xs font-normal text-zinc-500">{t("일")}</span>
          </div>
        </div>
        <div className="text-right font-mono text-xs text-zinc-500">
          <div>{t("최고 {n}일", { n: streak.best })}</div>
          {streak.atRisk && <div className="mt-0.5 text-amber-300">{t("오늘 운동하면 이어져요")}</div>}
        </div>
      </div>

      <div>
        <h2 className="mb-2.5 flex justify-between font-mono text-xs uppercase tracking-widest text-zinc-500">
          <span>WEEKLY QUESTS</span>
          <span className="normal-case tracking-normal">
            {doneCount}/{quests.length}
          </span>
        </h2>
        <ul className="space-y-3">
          {quests.map((q) => (
            <QuestRow key={q.id} q={q} />
          ))}
        </ul>
      </div>

      {weekPRs.length > 0 && (
        <div>
          <h2 className="mb-2 font-mono text-xs uppercase tracking-widest text-zinc-500">{t("이번 주 신기록")}</h2>
          <ul className="space-y-1.5 font-mono text-xs text-zinc-300">
            {weekPRs.map((p) => (
              <li key={`${p.date}-${p.title}`} className="flex justify-between gap-2">
                <span>🏆 {p.title}</span>
                <span className="shrink-0 text-zinc-500">{prLabel(p, t)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <p className="font-mono text-[10px] leading-relaxed text-zinc-600">
        {t("이 기기에 저장된 기록 기준입니다. 신기록은 같은 이름의 운동끼리 비교하며, 중량 운동은 추정 1RM(Epley), 맨몸 운동은 횟수로 계산해요.")}
      </p>
    </section>
  );
}

export function prLabel(p: GameState["weekPRs"][number], t: (k: string, v?: Record<string, string | number>) => string): string {
  return p.bodyweight
    ? t("{reps}회 (이전 {prev}회)", { reps: p.best.reps, prev: Math.round(p.previous) })
    : `${p.best.weightKg}kg×${p.best.reps}`;
}

"use client";

import { motion } from "framer-motion";
import { haptic } from "@/lib/haptic";
import type { SessionBlock } from "@/lib/types";
import Stepper from "./Stepper";
import { useT } from "@/lib/i18n";

const RPE_HINT: Record<number, string> = { 1: "아주 가벼움", 3: "가벼움", 5: "보통", 7: "힘듦", 9: "매우 힘듦", 10: "한계" };
const hint = (rpe: number) => {
  const keys = Object.keys(RPE_HINT).map(Number).filter((k) => k <= rpe);
  return RPE_HINT[keys[keys.length - 1] ?? 1];
};

export default function SessionBlockView({
  block,
  onChange,
}: {
  block: SessionBlock;
  onChange: (b: SessionBlock) => void;
}) {
  const t = useT();
  const done = block.doneAt !== null;
  const { minutes, rpe } = block.plan;

  const toggle = () => {
    haptic(done ? 8 : [20, 30, 40]);
    onChange({ ...block, doneAt: done ? null : Date.now() });
  };
  const setPlan = (patch: Partial<SessionBlock["plan"]>) => onChange({ ...block, plan: { ...block.plan, ...patch } });

  return (
    <div className="space-y-2.5">
      <div className="flex items-center gap-3">
        <motion.button
          type="button"
          aria-pressed={done}
          aria-label={done ? t("세션 완료 취소") : t("세션 완료")}
          whileTap={{ scale: 0.85 }}
          animate={done ? { scale: [1, 1.2, 1] } : { scale: 1 }}
          transition={{ type: "spring", stiffness: 500, damping: 18 }}
          onClick={toggle}
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border text-lg transition-colors ${
            done ? "border-neon bg-neon font-bold text-black shadow-neon" : "border-line bg-ink text-zinc-500"
          }`}
        >
          {done ? "✓" : "○"}
        </motion.button>
        <div className="min-w-0 flex-1">
          <h3 className={`truncate font-semibold ${done ? "text-neon" : "text-zinc-100"}`}>{block.title}</h3>
          <p className="font-mono text-xs text-zinc-500">
            {t("{m}분 · RPE {rpe} ({hint}) · 부하 {load} AU", { m: minutes, rpe, hint: t(hint(rpe)), load: Math.round(minutes * rpe) })}
          </p>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Stepper label="시간" value={minutes} step={5} min={5} max={600} unit="분" onChange={(v) => setPlan({ minutes: v })} />
        <Stepper label="RPE" value={rpe} step={1} min={1} max={10} unit="" onChange={(v) => setPlan({ rpe: v })} />
      </div>
    </div>
  );
}

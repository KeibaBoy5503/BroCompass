"use client";

import { motion } from "framer-motion";
import { haptic } from "@/lib/haptic";
import type { MealBlock } from "@/lib/types";
import { useT } from "@/lib/i18n";

export default function MealBlockView({
  block,
  onChange,
}: {
  block: MealBlock;
  onChange: (b: MealBlock) => void;
}) {
  const t = useT();
  const eaten = block.eatenAt !== null;
  const { kcal, proteinG, carbG, fatG } = block.plan;

  const toggle = () => {
    haptic(eaten ? 8 : [20, 30, 40]);
    onChange({ ...block, eatenAt: eaten ? null : Date.now() });
  };

  return (
    <div className="flex items-center gap-3">
      <motion.button
        type="button"
        aria-pressed={eaten}
        aria-label={eaten ? t("섭취 취소") : t("섭취 완료")}
        whileTap={{ scale: 0.85 }}
        animate={eaten ? { scale: [1, 1.2, 1] } : { scale: 1 }}
        transition={{ type: "spring", stiffness: 500, damping: 18 }}
        onClick={toggle}
        className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border text-lg transition-colors ${
          eaten
            ? "border-neon bg-neon font-bold text-black shadow-neon"
            : "border-line bg-ink text-zinc-500"
        }`}
      >
        {eaten ? "✓" : "○"}
      </motion.button>

      <div className="min-w-0 flex-1">
        <h3 className={`truncate font-semibold ${eaten ? "text-neon" : "text-zinc-100"}`}>
          {block.title}
        </h3>
        <p className="font-mono text-xs text-zinc-500">
          {kcal}kcal
          {proteinG > 0 && ` · P ${proteinG}`}
          {carbG > 0 && ` · C ${carbG}`}
          {fatG > 0 && ` · F ${fatG}`}
        </p>
      </div>
    </div>
  );
}

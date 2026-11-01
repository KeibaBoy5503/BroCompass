"use client";

import { motion } from "framer-motion";
import { haptic } from "@/lib/haptic";
import { useT } from "@/lib/i18n";

export default function Stepper({
  value,
  step,
  min = 0,
  max = 999,
  unit,
  label,
  onChange,
}: {
  value: number;
  step: number;
  min?: number;
  max?: number;
  unit: string;
  label: string;
  onChange: (v: number) => void;
}) {
  const t = useT();
  // 부동소수점 오차(0.1+0.2 등) 방지
  const clamp = (v: number) => Math.min(max, Math.max(min, Math.round(v * 100) / 100));
  const bump = (d: number) => {
    const next = clamp(value + d);
    if (next !== value) {
      haptic(8);
      onChange(next);
    }
  };

  const btn =
    "flex h-10 w-10 items-center justify-center rounded-lg border border-line bg-ink text-lg text-zinc-300 disabled:opacity-30";

  return (
    <div className="flex items-center gap-1.5">
      <motion.button
        type="button"
        whileTap={{ scale: 0.85 }}
        aria-label={t("{label} 감소", { label: t(label) })}
        disabled={value <= min}
        onClick={() => bump(-step)}
        className={btn}
      >
        −
      </motion.button>
      <div className="w-16 text-center font-mono text-sm text-zinc-100">
        {value}
        <span className="ml-0.5 text-xs text-zinc-500">{t(unit)}</span>
      </div>
      <motion.button
        type="button"
        whileTap={{ scale: 0.85 }}
        aria-label={t("{label} 증가", { label: t(label) })}
        disabled={value >= max}
        onClick={() => bump(step)}
        className={btn}
      >
        +
      </motion.button>
    </div>
  );
}

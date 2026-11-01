"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { haptic } from "@/lib/haptic";
import type { SetLog, WorkoutBlock } from "@/lib/types";
import Stepper from "./Stepper";
import { useT } from "@/lib/i18n";

export default function WorkoutBlockView({
  block,
  onChange,
}: {
  block: WorkoutBlock;
  onChange: (b: WorkoutBlock) => void;
}) {
  const t = useT();
  const { sets, reps, weightKg } = block.plan;
  const [editing, setEditing] = useState(false);

  const logByIdx = new Map(block.logs.map((l) => [l.setIndex, l]));
  const allDone = logByIdx.size >= sets;

  // 실제값이 플랜과 다른 세트가 있는지 (칩에 표시)
  const actual = (l: SetLog) => ({
    reps: l.reps ?? reps,
    weightKg: l.weightKg ?? weightKg,
  });

  const toggle = (i: number) => {
    if (logByIdx.has(i)) {
      haptic(8);
      onChange({ ...block, logs: block.logs.filter((l) => l.setIndex !== i) });
      return;
    }
    const willFinish = logByIdx.size + 1 >= sets;
    haptic(willFinish ? [30, 40, 30, 40, 60] : 25);

    // 기본값: 가장 최근에 완료한 세트의 실제값, 없으면 플랜 값
    const last = [...block.logs].sort((a, b) => b.completedAt - a.completedAt)[0];
    const base = last ? actual(last) : { reps, weightKg };
    onChange({
      ...block,
      logs: [
        ...block.logs,
        { setIndex: i, completedAt: Date.now(), reps: base.reps, weightKg: base.weightKg },
      ],
    });
  };

  const patchLog = (i: number, patch: Partial<SetLog>) =>
    onChange({
      ...block,
      logs: block.logs.map((l) => (l.setIndex === i ? { ...l, ...patch } : l)),
    });

  const doneSorted = [...block.logs].sort((a, b) => a.setIndex - b.setIndex);

  return (
    <div>
      <div className="flex items-baseline justify-between gap-2">
        <h3 className={`font-semibold ${allDone ? "text-neon" : "text-zinc-100"}`}>
          {block.title}
        </h3>
        <span className="shrink-0 font-mono text-xs text-zinc-500">
          {sets}×{reps}
          {weightKg > 0 ? ` · ${weightKg}kg` : ` · ${t("맨몸")}`}
        </span>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {Array.from({ length: sets }, (_, i) => {
          const log = logByIdx.get(i);
          const done = !!log;
          const a = log ? actual(log) : null;
          const changed = a && (a.reps !== reps || a.weightKg !== weightKg);
          return (
            <motion.button
              key={i}
              type="button"
              aria-pressed={done}
              aria-label={done ? t("{n}세트 완료됨", { n: i + 1 }) : t("{n}세트 미완료", { n: i + 1 })}
              whileTap={{ scale: 0.82 }}
              animate={done ? { scale: [1, 1.25, 1] } : { scale: 1 }}
              transition={{ type: "spring", stiffness: 500, damping: 18 }}
              onClick={() => toggle(i)}
              className={`relative flex h-12 w-12 items-center justify-center rounded-xl border font-mono text-sm transition-colors ${
                done
                  ? "border-neon bg-neon text-black shadow-neon"
                  : "border-line bg-ink text-zinc-400"
              }`}
            >
              <AnimatePresence initial={false} mode="wait">
                {done ? (
                  <motion.span
                    key="c"
                    initial={{ scale: 0, rotate: -45 }}
                    animate={{ scale: 1, rotate: 0 }}
                    exit={{ scale: 0 }}
                    className="font-bold"
                  >
                    ✓
                  </motion.span>
                ) : (
                  <motion.span key="n" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    {i + 1}
                  </motion.span>
                )}
              </AnimatePresence>
              {changed && (
                <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-amber-400 shadow-[0_0_6px_#FBBF24]" />
              )}
            </motion.button>
          );
        })}
      </div>

      {doneSorted.length > 0 && (
        <button
          type="button"
          onClick={() => {
            haptic(8);
            setEditing((v) => !v);
          }}
          className="mt-3 font-mono text-xs text-zinc-500 hover:text-neon"
        >
          {editing ? t("▲ 기록 접기") : t("▼ 실제 기록 수정 ({n}세트)", { n: doneSorted.length })}
        </button>
      )}

      <AnimatePresence initial={false}>
        {editing && doneSorted.length > 0 && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <ul className="mt-2 space-y-2">
              {doneSorted.map((l) => {
                const a = actual(l);
                return (
                  <li
                    key={l.setIndex}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-line bg-ink p-2"
                  >
                    <span className="w-10 font-mono text-xs text-neon">
                      {t("{n}세트", { n: l.setIndex + 1 })}
                    </span>
                    <Stepper
                      label="중량"
                      value={a.weightKg}
                      step={2.5}
                      max={500}
                      unit="kg"
                      onChange={(v) => patchLog(l.setIndex, { weightKg: v })}
                    />
                    <Stepper
                      label="횟수"
                      value={a.reps}
                      step={1}
                      min={1}
                      max={100}
                      unit="회"
                      onChange={(v) => patchLog(l.setIndex, { reps: v })}
                    />
                  </li>
                );
              })}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

"use client";

import { motion } from "framer-motion";
import type { CalcResult } from "@/lib/api";
import { useT } from "@/lib/i18n";

function MacroBar({
  label,
  grams,
  kcal,
  total,
  color,
}: {
  label: string;
  grams: number;
  kcal: number;
  total: number;
  color: string;
}) {
  const t = useT();
  const pct = total > 0 ? Math.round((kcal / total) * 100) : 0;
  return (
    <div>
      <div className="mb-1 flex justify-between font-mono text-sm">
        <span className="text-zinc-400">{t(label)}</span>
        <span>
          <b className="text-zinc-100">{grams}g</b>
          <span className="ml-2 text-zinc-500">{pct}%</span>
        </span>
      </div>
      <div className="h-2.5 overflow-hidden rounded-full bg-line">
        <motion.div
          className="h-full rounded-full"
          style={{ background: color, boxShadow: `0 0 8px ${color}` }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

export default function Dashboard({ result }: { result: CalcResult }) {
  const t = useT();
  const total = result.target_kcal;
  const pKcal = result.protein_g * 4;
  const cKcal = result.carb_g * 4;
  const fKcal = result.fat_g * 9;
  const diff = Math.round(result.target_kcal - result.tdee);

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="space-y-5 rounded-2xl border border-line bg-panel p-5"
    >
      <div className="grid grid-cols-2 gap-3 text-center">
        <Stat label="BMR" value={Math.round(result.bmr)} unit="kcal" />
        <Stat label="TDEE" value={Math.round(result.tdee)} unit="kcal" />
      </div>

      <div className="rounded-xl border border-neon/40 bg-neon/5 p-4 text-center shadow-neon">
        <div className="font-mono text-xs uppercase tracking-widest text-zinc-400">
          {t("목표 칼로리")}
        </div>
        <div className="mt-1 text-4xl font-bold text-neon">
          {Math.round(result.target_kcal)}
          <span className="ml-1 text-base text-zinc-400">kcal</span>
        </div>
        <div className="mt-1 font-mono text-xs text-zinc-500">
          {t("TDEE 대비 {diff} kcal", { diff: `${diff > 0 ? "+" : ""}${diff}` })}
        </div>
      </div>

      <div className="space-y-4">
        <MacroBar label="단백질" grams={result.protein_g} kcal={pKcal} total={total} color="#39FF88" />
        <MacroBar label="탄수화물" grams={result.carb_g} kcal={cKcal} total={total} color="#38BDF8" />
        <MacroBar label="지방" grams={result.fat_g} kcal={fKcal} total={total} color="#FBBF24" />
      </div>
    </motion.section>
  );
}

function Stat({ label, value, unit }: { label: string; value: number; unit: string }) {
  return (
    <div className="rounded-xl border border-line p-3">
      <div className="font-mono text-xs uppercase tracking-widest text-zinc-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">
        {value}
        <span className="ml-1 text-xs text-zinc-500">{unit}</span>
      </div>
    </div>
  );
}

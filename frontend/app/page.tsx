"use client";

import Link from "next/link";
import { useState } from "react";
import CalcForm from "@/components/CalcForm";
import Dashboard from "@/components/Dashboard";
import Logo from "@/components/Logo";
import { fetchCalc, type CalcInput, type CalcResult } from "@/lib/api";
import { haptic } from "@/lib/haptic";
import { saveCalcProfile } from "@/lib/profile";
import { useT } from "@/lib/i18n";

export default function Home() {
  const t = useT();
  const [result, setResult] = useState<CalcResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handle = async (input: CalcInput) => {
    setLoading(true);
    setError(null);
    try {
      const r = await fetchCalc(input);
      setResult(r);
      saveCalcProfile({ tdee: r.tdee, weightKg: input.weight_kg, bodyFatPct: input.body_fat_pct });
      haptic(40);
    } catch (e) {
      setError(e instanceof Error ? e.message : t("알 수 없는 오류"));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-md space-y-6 px-4 pb-24 pt-8 md:max-w-3xl md:grid md:grid-cols-2 md:gap-8 md:space-y-0">
      <div className="space-y-6">
        <header className="flex items-center gap-3">
          <Logo />
          <div>
            <h1 className="text-xl font-bold tracking-tight">
              Bro<span className="text-neon">Compass</span>
            </h1>
            <p className="font-mono text-xs text-zinc-500">TDEE · MACRO CALCULATOR</p>
          </div>
        </header>
        <Link
          href="/note"
          className="block rounded-lg border border-neon/40 bg-neon/5 py-3 text-center font-mono text-sm text-neon transition hover:shadow-neon"
        >
          {t("오늘의 데일리 노트 열기 →")}
        </Link>
        <Link
          href="/coach"
          className="block rounded-lg border border-line bg-panel py-3 text-center font-mono text-sm text-zinc-300 transition hover:border-neon hover:text-neon"
        >
          {t("논문 기반 코치 열기 →")}
        </Link>
        <CalcForm onSubmit={handle} loading={loading} />
      </div>

      <div className="mt-6 md:mt-0">
        {error && (
          <p className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-300">
            {error}
          </p>
        )}
        {result ? (
          <Dashboard result={result} />
        ) : (
          <div className="flex h-48 items-center justify-center rounded-2xl border border-dashed border-line font-mono text-sm text-zinc-600 md:h-full">
            {t("결과가 여기에 표시됩니다")}
          </div>
        )}
      </div>
    </main>
  );
}

"use client";

import { useEffect, useMemo, useState } from "react";
import BodyGauge from "@/components/diet/BodyGauge";
import WeightCurve from "@/components/diet/WeightCurve";
import Logo from "@/components/Logo";
import { planDiet } from "@/lib/diet";
import { useT } from "@/lib/i18n";
import { readCalcProfile, type CalcProfile } from "@/lib/profile";

const KEY = "brocompass:diet:inputs";
type Form = { weight: string; bf: string; target: string; tdee: string; pct: string };
const fromProfile = (p: CalcProfile): Partial<Form> => ({
  tdee: String(p.tdee),
  weight: String(p.weightKg),
  ...(p.bodyFatPct ? { bf: String(p.bodyFatPct) } : {}),
});
const DEFAULT: Form = { weight: "75", bf: "22", target: "15", tdee: "2600", pct: "0.7" };

const Field = ({
  label,
  unit,
  value,
  onChange,
  step = "0.1",
}: {
  label: string;
  unit: string;
  value: string;
  onChange: (v: string) => void;
  step?: string;
}) => (
  <label className="block">
    <span className="mb-1.5 block font-mono text-xs uppercase tracking-wider text-zinc-500">{label}</span>
    <div className="flex items-center rounded-lg border border-line bg-ink px-3 focus-within:border-neon">
      <input
        type="number"
        inputMode="decimal"
        step={step}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-transparent py-2.5 font-mono text-zinc-100 outline-none"
      />
      <span className="ml-2 font-mono text-xs text-zinc-500">{unit}</span>
    </div>
  </label>
);

export default function DietPage() {
  const t = useT();
  const [f, setF] = useState<Form>(DEFAULT);
  const [loaded, setLoaded] = useState(false);
  const [profile, setProfile] = useState<CalcProfile | null>(null);

  useEffect(() => {
    const prof = readCalcProfile();
    setProfile(prof);
    let hadSaved = false;
    try {
      const raw = localStorage.getItem(KEY);
      hadSaved = !!raw;
      if (raw) {
        const p = JSON.parse(raw);
        if (p && typeof p === "object") setF({ ...DEFAULT, ...Object.fromEntries(Object.entries(p).filter(([, v]) => typeof v === "string")) });
      }
    } catch {
      /* 저장소를 못 읽으면 기본값 사용 */
    }
    // 처음 열었고 계산기 결과가 있으면 그 값으로 채운다.
    if (!hadSaved && prof) setF((p) => ({ ...p, ...fromProfile(prof) }));
    setLoaded(true);
  }, []);
  useEffect(() => {
    if (!loaded) return;
    try {
      localStorage.setItem(KEY, JSON.stringify(f));
    } catch {
      /* 무시 */
    }
  }, [f, loaded]);

  const set = (k: keyof Form) => (v: string) => setF((p) => ({ ...p, [k]: v }));
  const result = useMemo(
    () =>
      planDiet({
        weightKg: Number(f.weight),
        bodyFatPct: Number(f.bf),
        targetBodyFatPct: Number(f.target),
        maintenanceKcal: Number(f.tdee),
        weeklyLossPct: Number(f.pct),
      }),
    [f]
  );

  const valid = Number.isFinite(Number(f.bf)) && f.bf !== "" ? Number(f.bf) : 0;
  const validT = Number.isFinite(Number(f.target)) && f.target !== "" ? Number(f.target) : 0;

  return (
    <main className="mx-auto max-w-md space-y-5 px-4 pb-24 pt-8 md:max-w-2xl lg:max-w-5xl">
      <header className="flex items-center gap-3">
        <Logo size={36} />
        <div>
          <h1 className="text-lg font-bold tracking-tight">
            Diet <span className="text-neon">Planner</span>
          </h1>
          <p className="font-mono text-xs text-zinc-500">{t("현재 → 목표 체지방 · 기간 · 칼로리")}</p>
        </div>
      </header>

      <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-6">
        <div className="space-y-5">
          <section className="rounded-2xl border border-line bg-panel p-4">
            <div className="grid grid-cols-2 items-end gap-4">
              <BodyGauge pct={valid} label={t("현재")} color="#FBBF24" />
              <BodyGauge pct={validT} label={t("목표")} color="#39FF88" />
            </div>
          </section>

          {result.ok ? (
            <section className="space-y-4 rounded-2xl border border-line bg-panel p-4">
              <div className="grid grid-cols-2 gap-3 font-mono sm:grid-cols-4">
                <Stat label={t("예상 기간")} value={`${result.plan.days}`} unit={t("일")} sub={t("약 {n}주", { n: result.plan.weeks })} />
                <Stat label={t("목표 체중")} value={`${result.plan.targetWeightKg}`} unit="kg" sub={t("제지방 유지 가정")} />
                <Stat label={t("빼야 할 체중")} value={`${result.plan.loseKg}`} unit="kg" />
                <Stat label={t("하루 섭취")} value={result.plan.dailyIntake.toLocaleString()} unit="kcal" sub={`−${result.plan.dailyDeficit} (${result.plan.deficitPct}%)`} />
              </div>
              <WeightCurve curve={result.plan.curve} />
              {result.plan.warnings.length > 0 && (
                <ul role="alert" className="space-y-1.5 rounded-xl border border-amber-400/30 bg-amber-400/5 p-3 text-xs leading-relaxed text-amber-200">
                  {result.plan.warnings.map((w) => (
                    <li key={w.key}>⚠ {t(w.key, w.vars)}</li>
                  ))}
                </ul>
              )}
            </section>
          ) : (
            <p role="alert" className="rounded-xl border border-red-400/30 bg-red-400/5 p-3 font-mono text-xs text-red-300">
              {t(result.error)}
            </p>
          )}
        </div>

        <div className="mt-5 space-y-4 rounded-2xl border border-line bg-panel p-4 lg:mt-0 lg:self-start">
          {profile && (
            <button
              type="button"
              onClick={() => setF((p) => ({ ...p, ...fromProfile(profile) }))}
              className="w-full rounded-lg border border-neon/40 bg-neon/5 py-2.5 font-mono text-xs text-neon transition hover:shadow-neon"
            >
              {t("계산기 값 불러오기")} · TDEE {profile.tdee.toLocaleString()} · {profile.weightKg}kg
              {profile.bodyFatPct ? ` · ${profile.bodyFatPct}%` : ""}
            </button>
          )}
          <Field label={t("체중")} unit="kg" value={f.weight} onChange={set("weight")} />
          <Field label={t("현재 체지방률")} unit="%" value={f.bf} onChange={set("bf")} />
          <Field label={t("목표 체지방률")} unit="%" value={f.target} onChange={set("target")} />
          <Field label={t("유지 칼로리 (TDEE)")} unit="kcal" value={f.tdee} onChange={set("tdee")} step="10" />
          <Field label={t("주당 감량 속도 (체중 대비)")} unit="%" value={f.pct} onChange={set("pct")} step="0.05" />
          <p className="font-mono text-[11px] leading-relaxed text-zinc-600">
            {t("유지 칼로리는 계산기에서 계산한 TDEE를 불러올 수 있어요. 일반적인 추정치이며 의료적 조언이 아닙니다. 체지방 1kg을 약 7,700kcal로 보고, 제지방량은 그대로라고 가정해요. 실제로는 감량 속도가 점점 느려지는 경우가 많아요.")}
          </p>
        </div>
      </div>
    </main>
  );
}

function Stat({ label, value, unit, sub }: { label: string; value: string; unit: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-line bg-ink px-3 py-2.5">
      <div className="text-[10px] text-zinc-500">{label}</div>
      <div className="mt-0.5 text-xl font-bold text-neon">
        {value}
        <span className="ml-1 text-xs font-normal text-zinc-500">{unit}</span>
      </div>
      {sub && <div className="text-[10px] text-zinc-600">{sub}</div>}
    </div>
  );
}

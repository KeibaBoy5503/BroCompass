"use client";

import { MUSCLES, WEEKLY_SETS_TARGET, type MuscleKey } from "@/lib/muscles";
import { useT } from "@/lib/i18n";

// 0세트 = 어둡게, 1~9세트 = 노랑, 10세트 이상 = 네온 그린. 색만으로 구분하지 않도록 세트 수도 함께 적는다.
const tone = (n: number) =>
  n >= WEEKLY_SETS_TARGET
    ? "border-neon/60 bg-neon/10 text-neon"
    : n > 0
      ? "border-amber-400/50 bg-amber-400/10 text-amber-300"
      : "border-line bg-ink text-zinc-600";

export default function MuscleHeat({
  sets,
  unclassified,
}: {
  sets: Record<MuscleKey, number>;
  unclassified: number;
}) {
  const t = useT();
  return (
    <section className="space-y-3 rounded-2xl border border-line bg-panel p-4">
      <h2 className="flex justify-between font-mono text-xs uppercase tracking-widest text-zinc-500">
        <span>{t("MUSCLE MAP · 7일")}</span>
        <span className="normal-case tracking-normal">{t("목표 {n}세트", { n: WEEKLY_SETS_TARGET })}</span>
      </h2>
      <div className="grid grid-cols-3 gap-2">
        {MUSCLES.map((m) => (
          <div key={m.key} className={`rounded-lg border px-2 py-2 text-center font-mono ${tone(sets[m.key])}`}>
            <div className="text-[10px] leading-tight">{t(m.label)}</div>
            <div className="mt-0.5 text-sm font-bold">{sets[m.key]}</div>
          </div>
        ))}
      </div>
      {unclassified > 0 && (
        <p className="font-mono text-[10px] text-zinc-600">{t("부위를 알 수 없는 운동 {n}세트는 제외했어요.", { n: unclassified })}</p>
      )}
    </section>
  );
}

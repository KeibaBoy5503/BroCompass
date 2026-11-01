"use client";

import { useT } from "@/lib/i18n";

/** 주별 예상 체중 곡선. 단순 직선 감량 가정이라 실제로는 속도가 점점 느려지는 경우가 많다. */
export default function WeightCurve({ curve }: { curve: number[] }) {
  const t = useT();
  if (curve.length < 2) return null;
  const W = 300;
  const H = 90;
  const max = Math.max(...curve);
  const min = Math.min(...curve);
  const span = Math.max(max - min, 0.1);
  const pts = curve.map((v, i) => [(i / (curve.length - 1)) * W, 6 + ((max - v) / span) * (H - 12)] as const);
  const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-24 w-full" role="img" aria-label={t("주별 예상 체중 곡선")}>
        <path d={d} fill="none" stroke="#39FF88" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx={pts[0][0]} cy={pts[0][1]} r="3" fill="#39FF88" />
        <circle cx={pts[pts.length - 1][0]} cy={pts[pts.length - 1][1]} r="3" fill="#FB7185" />
      </svg>
      <div className="flex justify-between font-mono text-[11px] text-zinc-500">
        <span>{t("시작 {w}kg", { w: curve[0] })}</span>
        <span>
          {t("{n}주 후 {w}kg", { n: curve.length - 1, w: curve[curve.length - 1] })}
        </span>
      </div>
    </div>
  );
}

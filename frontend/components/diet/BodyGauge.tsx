"use client";

import { motion } from "framer-motion";
import { useId } from "react";
import { useT } from "@/lib/i18n";

// 체지방률 5%~40% 범위를 몸통 높이(아래→위)에 대응시킨 게이지. 해부학적 분포가 아니라 수치를 한눈에 보여주는 용도다.
const MIN = 5;
const MAX = 40;
const fraction = (pct: number) => Math.min(Math.max((pct - MIN) / (MAX - MIN), 0), 1);

const Body = () => (
  <>
    <circle cx="50" cy="16" r="11" />
    <rect x="30" y="30" width="40" height="62" rx="16" />
    <rect x="12" y="32" width="14" height="60" rx="7" />
    <rect x="74" y="32" width="14" height="60" rx="7" />
    <rect x="32" y="90" width="16" height="96" rx="8" />
    <rect x="52" y="90" width="16" height="96" rx="8" />
  </>
);

export default function BodyGauge({
  pct,
  label,
  color,
}: {
  pct: number;
  label: string;
  color: string;
}) {
  const t = useT();
  const id = useId().replace(/:/g, "");
  const H = 190;
  const fillH = H * fraction(pct);
  return (
    <figure className="flex flex-col items-center">
      <svg
        viewBox="0 0 100 192"
        className="h-56 w-auto"
        role="img"
        aria-label={t("{label} 체지방률 {pct}%", { label, pct })}
      >
        <defs>
          <clipPath id={`c-${id}`}>
            <motion.rect
              x="0"
              width="100"
              initial={false}
              animate={{ y: H - fillH, height: fillH }}
              transition={{ type: "spring", stiffness: 90, damping: 18 }}
            />
          </clipPath>
        </defs>
        <g fill="#16161a" stroke="#2c2c32" strokeWidth="1">
          <Body />
        </g>
        <g fill={color} clipPath={`url(#c-${id})`} opacity="0.9">
          <Body />
        </g>
      </svg>
      <figcaption className="mt-2 text-center font-mono">
        <div className="text-xs text-zinc-500">{label}</div>
        <div className="text-2xl font-bold" style={{ color }}>
          {pct}
          <span className="ml-0.5 text-sm text-zinc-500">%</span>
        </div>
      </figcaption>
    </figure>
  );
}

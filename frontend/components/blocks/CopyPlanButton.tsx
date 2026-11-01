"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { cloneForToday } from "@/lib/copyPlan";
import { haptic } from "@/lib/haptic";
import { findPreviousNote } from "@/lib/previousNote";
import type { Block } from "@/lib/types";
import { useT } from "@/lib/i18n";

/** 가장 가까운 이전 기록의 '계획'을 현재 날짜로 복사한다. 날짜가 바뀌면 key 로 초기화된다. */
export default function CopyPlanButton({
  date,
  onCopy,
  prominent,
}: {
  date: string;
  onCopy: (blocks: Block[]) => void;
  prominent?: boolean;
}) {
  const t = useT();
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const run = async () => {
    if (busy || done) return;
    setBusy(true);
    setMsg(null);
    try {
      const prev = await findPreviousNote(date);
      if (!prev) {
        haptic(8);
        setMsg(t("최근 14일 안에 복사할 기록이 없어요."));
        return;
      }
      haptic([20, 30, 20]);
      onCopy(cloneForToday(prev.blocks));
      setDone(true);
      setMsg(t("{date} 계획 {n}개를 복사했어요. 체크는 비워뒀어요.", { date: prev.date, n: prev.blocks.length }));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <motion.button
        type="button"
        whileTap={{ scale: 0.96 }}
        disabled={busy || done}
        onClick={run}
        className={`rounded-xl border px-4 py-2.5 font-mono text-xs transition disabled:opacity-50 ${
          prominent
            ? "border-neon/50 bg-neon/10 text-neon hover:shadow-neon"
            : "border-line bg-panel text-zinc-400 hover:text-neon"
        }`}
      >
        {busy ? t("찾는 중...") : done ? t("복사됨") : t("⧉ 이전 계획 복사")}
      </motion.button>
      {msg && (
        <p role="status" className="mt-2 font-mono text-xs text-zinc-500">
          {msg}
        </p>
      )}
    </div>
  );
}

"use client";

import { motion } from "framer-motion";
import { haptic } from "@/lib/haptic";
import { isValidDate, shiftDate, todayStr, weekdayLabel } from "@/lib/date";
import { useT } from "@/lib/i18n";

export default function DateNav({
  date,
  onChange,
}: {
  date: string;
  onChange: (d: string) => void;
}) {
  const t = useT();
  const today = todayStr();
  const go = (d: string) => {
    haptic(10);
    onChange(d);
  };

  const arrow =
    "flex h-11 w-11 items-center justify-center rounded-xl border border-line bg-panel text-zinc-300";

  return (
    <div className="flex items-center gap-2">
      <motion.button
        type="button"
        whileTap={{ scale: 0.88 }}
        aria-label={t("전날")}
        onClick={() => go(shiftDate(date, -1))}
        className={arrow}
      >
        ‹
      </motion.button>

      <label className="relative flex h-11 flex-1 items-center justify-center rounded-xl border border-line bg-panel font-mono text-sm">
        <span className="pointer-events-none">
          {date} ({weekdayLabel(date)})
        </span>
        {/* 투명 date input 을 위에 덮어 탭하면 네이티브 날짜 선택기가 열린다 */}
        <input
          type="date"
          value={date}
          onChange={(e) => isValidDate(e.target.value) && go(e.target.value)}
          aria-label={t("날짜 선택")}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
        />
      </label>

      <motion.button
        type="button"
        whileTap={{ scale: 0.88 }}
        aria-label={t("다음날")}
        onClick={() => go(shiftDate(date, 1))}
        className={arrow}
      >
        ›
      </motion.button>

      {date !== today && (
        <motion.button
          type="button"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          whileTap={{ scale: 0.92 }}
          onClick={() => go(today)}
          className="h-11 shrink-0 rounded-xl border border-neon/50 bg-neon/10 px-3 font-mono text-xs text-neon"
        >
          {t("오늘")}
        </motion.button>
      )}
    </div>
  );
}

"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect } from "react";
import { useT } from "@/lib/i18n";

export type Toast = { id: number; title: string; detail: string };

/** 신기록 알림. 3.5초 뒤 자동으로 사라진다. */
export default function PrToast({ toast, onDone }: { toast: Toast | null; onDone: () => void }) {
  const t = useT();
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(onDone, 3500);
    return () => clearTimeout(t);
  }, [toast, onDone]);

  return (
    <div className="pointer-events-none fixed inset-x-0 top-4 z-50 flex justify-center px-4">
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.id}
            role="status"
            initial={{ opacity: 0, y: -24, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -16 }}
            transition={{ type: "spring", stiffness: 380, damping: 24 }}
            className="rounded-xl border border-neon/60 bg-panel px-4 py-3 text-center font-mono shadow-neon"
          >
            <div className="text-sm font-bold text-neon">{t("🏆 신기록!")}</div>
            <div className="mt-0.5 text-xs text-zinc-200">{toast.title}</div>
            <div className="text-[11px] text-zinc-500">{toast.detail}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

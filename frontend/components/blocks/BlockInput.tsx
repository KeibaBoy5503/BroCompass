"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { haptic } from "@/lib/haptic";
import { parseBlock } from "@/lib/parse";
import type { Block } from "@/lib/types";
import { useT } from "@/lib/i18n";

const EXAMPLES = ["벤치프레스 5x5 80", "닭가슴살 200kcal p40", "현미밥 300kcal p6 c65 f2"];

export default function BlockInput({ onAdd }: { onAdd: (b: Block) => void }) {
  const t = useT();
  const [value, setValue] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const block = parseBlock(value);
    if (!block) return;
    haptic(15);
    onAdd(block);
    setValue("");
  };

  return (
    <form onSubmit={submit} className="space-y-2">
      <div className="flex gap-2">
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={t("입력 후 Enter: 벤치프레스 5x5 80 · 스파링 60분 rpe7")}
          enterKeyHint="done"
          className="min-w-0 flex-1 rounded-xl border border-line bg-panel px-4 py-3 text-zinc-100 outline-none transition focus:border-neon focus:shadow-neon"
        />
        <motion.button
          type="submit"
          whileTap={{ scale: 0.92 }}
          className="shrink-0 rounded-xl bg-neon px-5 font-bold text-black shadow-neon"
        >
          {t("추가")}
        </motion.button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {EXAMPLES.map((ex) => (
          <button
            key={ex}
            type="button"
            onClick={() => setValue(t(ex))}
            className="rounded-full border border-line px-2.5 py-1 font-mono text-[11px] text-zinc-500 hover:text-neon"
          >
            {t(ex)}
          </button>
        ))}
      </div>
    </form>
  );
}

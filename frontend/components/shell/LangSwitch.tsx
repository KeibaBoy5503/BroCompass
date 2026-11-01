"use client";

import { LANGS } from "@/lib/translate";
import { useLang } from "@/lib/i18n";

/** 언어 전환. 현재 언어만 강조하고 aria-pressed 로 상태를 알린다. */
export default function LangSwitch({ className = "" }: { className?: string }) {
  const { lang, setLang } = useLang();
  return (
    <div role="group" aria-label="Language" className={`flex gap-1 font-mono text-[11px] ${className}`}>
      {LANGS.map((l) => (
        <button
          key={l.code}
          type="button"
          aria-pressed={lang === l.code}
          onClick={() => setLang(l.code)}
          className={`rounded-md border px-2 py-1 transition ${
            lang === l.code ? "border-neon/60 bg-neon/10 text-neon" : "border-line text-zinc-500 hover:text-zinc-200"
          }`}
        >
          {l.label}
        </button>
      ))}
    </div>
  );
}

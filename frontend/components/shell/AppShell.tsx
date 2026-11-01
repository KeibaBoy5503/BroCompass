"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import Logo from "@/components/Logo";
import LangSwitch from "@/components/shell/LangSwitch";
import { useT } from "@/lib/i18n";

const TABS = [
  { href: "/", label: "계산기", glyph: "∑" },
  { href: "/note", label: "노트", glyph: "▤" },
  { href: "/diet", label: "다이어트", glyph: "◐" },
  { href: "/coach", label: "코치", glyph: "◎" },
];

const isActive = (path: string, href: string) => (href === "/" ? path === "/" : path.startsWith(href));

/**
 * 앱 공통 틀. 넓은 화면(lg 이상)에서는 왼쪽 사이드바, 좁은 화면에서는 아래 탭바로 이동한다.
 * 페이지 본문은 그대로 두고 바깥만 감싸므로, 기존 페이지는 수정 없이 PC 화면에서도 같은 틀 안에 놓인다.
 */
export default function AppShell({ children }: { children: React.ReactNode }) {
  const tr = useT();
  const path = usePathname() ?? "/";
  return (
    <div className="lg:pl-56">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-56 flex-col border-r border-line bg-ink/95 p-5 lg:flex">
        <Link href="/" className="mb-8 flex items-center gap-3">
          <Logo size={34} />
          <span className="text-lg font-bold tracking-tight">
            Bro<span className="text-neon">Compass</span>
          </span>
        </Link>
        <nav className="space-y-1">
          {TABS.map((t) => {
            const on = isActive(path, t.href);
            return (
              <Link
                key={t.href}
                href={t.href}
                aria-current={on ? "page" : undefined}
                className={`flex items-center gap-3 rounded-lg px-3 py-2.5 font-mono text-sm transition ${
                  on ? "bg-neon/10 text-neon shadow-neon" : "text-zinc-400 hover:bg-panel hover:text-zinc-100"
                }`}
              >
                <span className="w-4 text-center">{t.glyph}</span>
                {tr(t.label)}
              </Link>
            );
          })}
        </nav>
        <LangSwitch className="mt-6 flex-wrap" />
        <p className="mt-auto font-mono text-[10px] leading-relaxed text-zinc-600">
          {tr("일반적인 추정치이며 의료적 조언이 아닙니다.")}
        </p>
      </aside>

      <div className="flex justify-end px-4 pt-3 lg:hidden">
        <LangSwitch />
      </div>
      {children}

      <nav className="fixed inset-x-0 bottom-0 z-30 flex border-t border-line bg-ink/95 backdrop-blur lg:hidden">
        {TABS.map((t) => {
          const on = isActive(path, t.href);
          return (
            <Link
              key={t.href}
              href={t.href}
              aria-current={on ? "page" : undefined}
              className={`flex flex-1 flex-col items-center gap-0.5 py-2.5 font-mono text-[11px] ${
                on ? "text-neon" : "text-zinc-500"
              }`}
            >
              <span className="text-base leading-none">{t.glyph}</span>
              {tr(t.label)}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}

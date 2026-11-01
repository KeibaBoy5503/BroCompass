import type { SyncState } from "@/lib/useDailyNote";
import { useT } from "@/lib/i18n";

const MAP: Record<SyncState, { label: string; dot: string }> = {
  idle: { label: "", dot: "bg-zinc-600" },
  syncing: { label: "동기화 중", dot: "bg-amber-400 animate-pulse" },
  synced: { label: "저장됨", dot: "bg-neon shadow-[0_0_6px_#39FF88]" },
  offline: { label: "오프라인 · 이 기기에만 저장", dot: "bg-red-400" },
};

export default function SyncBadge({ state }: { state: SyncState }) {
  const t = useT();
  const { label, dot } = MAP[state];
  if (!label) return null;
  return (
    <span role="status" className="flex items-center gap-1.5 font-mono text-[11px] text-zinc-500">
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {t(label)}
    </span>
  );
}

"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  TouchSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { AnimatePresence } from "framer-motion";
import GamePanel, { prLabel } from "@/components/game/GamePanel";
import MuscleHeat from "@/components/game/MuscleHeat";
import PrToast, { type Toast } from "@/components/game/PrToast";
import Logo from "@/components/Logo";
import BlockInput from "@/components/blocks/BlockInput";
import CopyPlanButton from "@/components/blocks/CopyPlanButton";
import DateNav from "@/components/blocks/DateNav";
import MealPhotoButton from "@/components/blocks/MealPhotoButton";
import SortableBlock from "@/components/blocks/SortableBlock";
import SummaryBar from "@/components/blocks/SummaryBar";
import SyncBadge from "@/components/blocks/SyncBadge";
import { todayStr } from "@/lib/date";
import { buildGameState, normName, withCurrent } from "@/lib/game";
import { loadAllLocal } from "@/lib/localNotes";
import type { DailyNote } from "@/lib/types";
import { haptic } from "@/lib/haptic";
import { weeklySetsByMuscle } from "@/lib/muscles";
import { summarize } from "@/lib/summary";
import { useDailyNote } from "@/lib/useDailyNote";
import { useT } from "@/lib/i18n";

export default function NotePage() {
  // 서버(다른 시간대)와 클라이언트의 '오늘'이 달라 hydration 불일치가 나지 않도록 마운트 후 결정한다.
  const [date, setDate] = useState<string | null>(null);
  useEffect(() => setDate(todayStr()), []);

  if (!date) return <main className="min-h-screen" />;
  return <NoteBody date={date} onDateChange={setDate} />;
}

function NoteBody({
  date,
  onDateChange,
}: {
  date: string;
  onDateChange: (d: string) => void;
}) {
  const t = useT();
  const { blocks, ready, sync, setBlocks, addBlock, addBlocks, removeBlock, updateBlock } =
    useDailyNote(date);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, { activationConstraint: { delay: 120, tolerance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const onDragEnd = (e: DragEndEvent) => {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    haptic(12);
    setBlocks((prev) => {
      const from = prev.findIndex((b) => b.id === active.id);
      const to = prev.findIndex((b) => b.id === over.id);
      return from < 0 || to < 0 ? prev : arrayMove(prev, from, to);
    });
  };

  const summary = useMemo(() => summarize(blocks), [blocks]);

  // --- 게임 피드백 (신기록·스트릭·퀘스트·레벨) ---
  // 이 기기에 저장된 노트를 날짜가 바뀔 때마다 다시 읽고, 지금 편집 중인 날짜는 화면 상태로 덮어쓴다.
  const [stored, setStored] = useState<DailyNote[]>([]);
  useEffect(() => setStored(loadAllLocal()), [date]);
  const realToday = useMemo(() => todayStr(), []);
  const game = useMemo(
    () => buildGameState(withCurrent(stored, { date, blocks, updatedAt: 0 }), realToday),
    [stored, date, blocks, realToday]
  );

  const muscles = useMemo(
    () => weeklySetsByMuscle(withCurrent(stored, { date, blocks, updatedAt: 0 }), realToday),
    [stored, date, blocks, realToday]
  );

  // 신기록 알림: 처음 불러온 기록은 '이미 본 것'으로 처리하고, 그 이후 새로 생긴 신기록만 축하한다.
  const seenPRs = useRef<{ date: string | null; keys: Set<string> }>({ date: null, keys: new Set() });
  const [toast, setToast] = useState<Toast | null>(null);
  const closeToast = useCallback(() => setToast(null), []);
  useEffect(() => {
    if (!ready || (sync !== "synced" && sync !== "offline")) return;
    const keyOf = (p: (typeof game.todayPRs)[number]) => `${p.date}|${normName(p.title)}|${p.score.toFixed(3)}`;
    const seen = seenPRs.current;
    if (seen.date !== date) {
      seen.date = date;
      seen.keys = new Set(game.todayPRs.map(keyOf));
      return;
    }
    const fresh = game.todayPRs.filter((p) => !seen.keys.has(keyOf(p)));
    if (fresh.length === 0) return;
    fresh.forEach((p) => seen.keys.add(keyOf(p)));
    const p = fresh[fresh.length - 1];
    haptic([20, 40, 20, 40, 90]);
    setToast({ id: Date.now(), title: p.title, detail: prLabel(p, t) });
  }, [game, ready, sync, date, t]);

  return (
    <main className="mx-auto max-w-md px-4 pb-24 pt-8 md:max-w-2xl lg:grid lg:max-w-6xl lg:grid-cols-[minmax(0,1fr)_340px] lg:gap-x-8 lg:px-8">
      <PrToast toast={toast} onDone={closeToast} />

      <div className="space-y-5 lg:col-start-1 lg:row-start-1">
        <header className="flex items-center gap-3">
          <Logo size={36} />
          <div>
            <h1 className="text-lg font-bold tracking-tight">
              Daily <span className="text-neon">Note</span>
            </h1>
            <SyncBadge state={sync} />
          </div>
        </header>

        <DateNav date={date} onChange={onDateChange} />

        <BlockInput onAdd={addBlock} />

        {ready && (
          <div className="flex flex-wrap items-start gap-3">
            <MealPhotoButton onAdd={addBlocks} />
            <CopyPlanButton
              key={date}
              date={date}
              onCopy={addBlocks}
              prominent={blocks.length === 0}
            />
          </div>
        )}
      </div>

      <aside className="mt-5 space-y-5 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:mt-0 lg:self-start lg:sticky lg:top-8">
        <SummaryBar summary={summary} />
        {ready && <GamePanel state={game} />}
        {ready && <MuscleHeat sets={muscles.sets} unclassified={muscles.unclassified} />}
      </aside>

      <div className="mt-5 lg:col-start-1 lg:row-start-2">
        {!ready ? null : blocks.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-line p-8 text-center font-mono text-sm text-zinc-600">
            {t("블럭이 없습니다. 위 입력창에 운동이나 식단을 한 줄로 적어보세요.")}
          </div>
        ) : (
          <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
            <SortableContext items={blocks.map((b) => b.id)} strategy={verticalListSortingStrategy}>
              <div className="space-y-3">
                <AnimatePresence initial={false}>
                  {blocks.map((b) => (
                    <SortableBlock
                      key={b.id}
                      block={b}
                      onChange={(next) => updateBlock(b.id, () => next)}
                      onRemove={() => removeBlock(b.id)}
                    />
                  ))}
                </AnimatePresence>
              </div>
            </SortableContext>
          </DndContext>
        )}
      </div>
    </main>
  );
}

"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { motion } from "framer-motion";
import { haptic } from "@/lib/haptic";
import type { Block, MealBlock, SessionBlock, WorkoutBlock } from "@/lib/types";
import MealBlockView from "./MealBlockView";
import SessionBlockView from "./SessionBlockView";
import WorkoutBlockView from "./WorkoutBlockView";
import { useT } from "@/lib/i18n";

export default function SortableBlock({
  block,
  onChange,
  onRemove,
}: {
  block: Block;
  onChange: (b: Block) => void;
  onRemove: () => void;
}) {
  const t = useT();
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id: block.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 10 : undefined,
  };

  const tag =
    t(
      block.kind === "workout" ? "운동" : block.kind === "meal" ? "식단" : block.kind === "session" ? "세션" : "메모"
    );

  return (
    <div ref={setNodeRef} style={style}>
      <motion.div
        layout="position"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0, scale: isDragging ? 1.02 : 1 }}
        exit={{ opacity: 0, x: -24 }}
        className={`flex gap-2 rounded-2xl border bg-panel p-3 ${
          isDragging ? "border-neon shadow-neon" : "border-line"
        }`}
      >
        {/* 드래그 핸들: 모바일 스크롤과 충돌하지 않도록 핸들에만 touch-action: none */}
        <button
          type="button"
          aria-label={t("순서 변경")}
          {...attributes}
          {...listeners}
          onPointerDown={(e) => {
            haptic(10);
            listeners?.onPointerDown?.(e);
          }}
          className="flex w-7 shrink-0 cursor-grab touch-none items-center justify-center text-zinc-600 active:cursor-grabbing"
        >
          ⋮⋮
        </button>

        <div className="min-w-0 flex-1">
          <div className="mb-1 flex items-center justify-between">
            <span className="font-mono text-[10px] uppercase tracking-widest text-zinc-600">
              {tag}
            </span>
            <button
              type="button"
              aria-label={t("블럭 삭제")}
              onClick={onRemove}
              className="px-1 text-zinc-600 hover:text-red-400"
            >
              ✕
            </button>
          </div>

          {block.kind === "workout" && (
            <WorkoutBlockView block={block as WorkoutBlock} onChange={onChange} />
          )}
          {block.kind === "meal" && (
            <MealBlockView block={block as MealBlock} onChange={onChange} />
          )}
          {block.kind === "session" && (
            <SessionBlockView block={block as SessionBlock} onChange={onChange} />
          )}
          {block.kind === "text" && <p className="text-zinc-300">{block.title}</p>}
        </div>
      </motion.div>
    </div>
  );
}

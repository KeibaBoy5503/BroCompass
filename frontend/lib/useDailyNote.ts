"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { readLocal, writeLocal } from "./localNotes";
import { fetchNote, pushNote } from "./notesApi";
import { decideSync } from "./syncPolicy";
import type { Block, DailyNote } from "./types";

export type SyncState = "idle" | "syncing" | "synced" | "offline";

const PUSH_DELAY_MS = 800;

/**
 * 로컬 우선(local-first) 데일리 노트.
 * - 모든 변경은 즉시 localStorage 에 저장되고, 잠시 뒤 서버로 올라간다.
 * - 서버가 꺼져 있어도 앱은 그대로 동작하고, 상태만 'offline'으로 표시된다.
 * - 기기 간 충돌은 updatedAt 이 더 최신인 쪽이 이긴다 (기기 시계가 크게 어긋나면 오판할 수 있음).
 */
export function useDailyNote(date: string) {
  const [blocks, setBlocks_] = useState<Block[]>([]);
  const [ready, setReady] = useState(false);
  const [sync, setSync] = useState<SyncState>("idle");

  const noteRef = useRef<DailyNote>({ date, blocks: [], updatedAt: 0 });
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const push = useCallback(async (note: DailyNote) => {
    const isCurrent = () => noteRef.current.date === note.date;
    if (isCurrent()) setSync("syncing");
    try {
      const winner = await pushNote(note);
      // 다른 기기가 더 최신으로 저장해 뒀다면 그쪽을 채택 (그 사이 내가 또 수정했다면 건드리지 않음)
      if (
        winner.updatedAt > note.updatedAt &&
        isCurrent() &&
        noteRef.current.updatedAt === note.updatedAt
      ) {
        noteRef.current = winner;
        writeLocal(winner);
        setBlocks_(winner.blocks);
      }
      if (isCurrent()) setSync("synced");
    } catch {
      if (isCurrent()) setSync("offline");
    }
  }, []);

  const flush = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
      void push(noteRef.current);
    }
  }, [push]);

  // 날짜 로드: 로컬을 즉시 보여주고, 서버와 비교해 동기화
  useEffect(() => {
    let cancelled = false;
    const local = readLocal(date) ?? { date, blocks: [], updatedAt: 0 };
    noteRef.current = local;
    setBlocks_(local.blocks);
    setReady(true);
    setSync("syncing");

    (async () => {
      try {
        const remote = await fetchNote(date);
        if (cancelled) return;
        const action = decideSync(noteRef.current, remote);
        if (action === "adopt" && remote) {
          noteRef.current = remote;
          writeLocal(remote);
          setBlocks_(remote.blocks);
          setSync("synced");
        } else if (action === "push") {
          await push(noteRef.current);
        } else {
          setSync("synced");
        }
      } catch {
        if (!cancelled) setSync("offline");
      }
    })();

    return () => {
      cancelled = true;
      flush(); // 날짜를 바꾸거나 페이지를 떠나기 전에 대기 중인 저장을 바로 올림
    };
  }, [date, push, flush]);

  const commit = useCallback(
    (next: Block[]) => {
      const note: DailyNote = { date: noteRef.current.date, blocks: next, updatedAt: Date.now() };
      noteRef.current = note;
      setBlocks_(next);
      writeLocal(note);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        void push(noteRef.current);
      }, PUSH_DELAY_MS);
    },
    [push]
  );

  const setBlocks = useCallback(
    (updater: Block[] | ((prev: Block[]) => Block[])) =>
      commit(typeof updater === "function" ? updater(noteRef.current.blocks) : updater),
    [commit]
  );

  const addBlock = useCallback((b: Block) => setBlocks((p) => [...p, b]), [setBlocks]);
  const addBlocks = useCallback((bs: Block[]) => setBlocks((p) => [...p, ...bs]), [setBlocks]);
  const removeBlock = useCallback(
    (id: string) => setBlocks((p) => p.filter((b) => b.id !== id)),
    [setBlocks]
  );
  const updateBlock = useCallback(
    (id: string, fn: (b: Block) => Block) =>
      setBlocks((p) => p.map((b) => (b.id === id ? fn(b) : b))),
    [setBlocks]
  );

  return { blocks, ready, sync, setBlocks, addBlock, addBlocks, removeBlock, updateBlock };
}

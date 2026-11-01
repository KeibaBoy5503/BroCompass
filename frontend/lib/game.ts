// 게임적 피드백(신기록·스트릭·주간 퀘스트·레벨) 계산. 화면과 무관한 순수 함수만 둔다.
// 모든 값은 사용자의 실제 기록에서만 계산하며, 기록이 없으면 보상도 없다.

import { shiftDate } from "./date";
import type { DailyNote, WorkoutBlock } from "./types";

export const normName = (t: string) => t.toLowerCase().replace(/\s+/g, "");

/** 세트 점수: 중량이 있으면 추정 1RM(Epley, 횟수는 12회까지만 반영), 맨몸이면 횟수. */
export function setScore(reps: number, weightKg: number): number {
  if (!(reps > 0)) return 0;
  return weightKg > 0 ? weightKg * (1 + Math.min(reps, 12) / 30) : reps;
}

type DoneSet = { reps: number; weightKg: number };

/** 완료한 세트의 실제 값 (없으면 플랜 값). */
export function doneSets(b: WorkoutBlock): DoneSet[] {
  return b.logs.map((l) => ({
    reps: l.reps ?? b.plan.reps,
    weightKg: l.weightKg ?? b.plan.weightKg,
  }));
}

export type PREvent = {
  date: string;
  title: string;
  score: number;
  previous: number;
  bodyweight: boolean;
  best: DoneSet; // 신기록을 만든 세트
};

const EPS = 1e-6;

/**
 * 오래된 순으로 노트를 훑으며 신기록을 찾는다.
 * 어떤 운동의 '첫 기록'은 신기록으로 치지 않는다 (비교 대상이 없으므로).
 * 같은 날 같은 운동은 한 번만 센다.
 */
export function findPRs(notesAsc: DailyNote[]): PREvent[] {
  const best = new Map<string, number>();
  const events: PREvent[] = [];
  for (const note of notesAsc) {
    const dayBest = new Map<string, { score: number; set: DoneSet; title: string }>();
    for (const b of note.blocks) {
      if (b.kind !== "workout") continue;
      const key = normName(b.title);
      if (!key) continue;
      for (const s of doneSets(b)) {
        const score = setScore(s.reps, s.weightKg);
        const cur = dayBest.get(key);
        if (score > 0 && (!cur || score > cur.score)) dayBest.set(key, { score, set: s, title: b.title });
      }
    }
    for (const [key, d] of dayBest) {
      const prev = best.get(key);
      if (prev !== undefined && d.score > prev + EPS) {
        events.push({
          date: note.date,
          title: d.title,
          score: d.score,
          previous: prev,
          bodyweight: d.set.weightKg <= 0,
          best: d.set,
        });
      }
      if (prev === undefined || d.score > prev) best.set(key, d.score);
    }
  }
  return events;
}

const hasDoneSet = (n: DailyNote) => n.blocks.some((b) => b.kind === "workout" && b.logs.length > 0);

/** 운동(완료 세트)을 한 날의 집합. */
export function activeDates(notes: DailyNote[]): Set<string> {
  return new Set(notes.filter(hasDoneSet).map((n) => n.date));
}

/**
 * 연속 운동일. 오늘 아직 운동 전이면 어제까지의 연속을 유지해서 보여준다
 * (하루가 끝나기 전에 스트릭이 0이 되면 의욕만 꺾이므로).
 */
export function calcStreak(active: Set<string>, today: string): { current: number; best: number; atRisk: boolean } {
  let cursor = active.has(today) ? today : shiftDate(today, -1);
  let current = 0;
  while (active.has(cursor)) {
    current++;
    cursor = shiftDate(cursor, -1);
  }
  const atRisk = current > 0 && !active.has(today);

  const sorted = [...active].sort();
  let best = 0;
  let run = 0;
  let prev: string | null = null;
  for (const d of sorted) {
    run = prev && shiftDate(prev, 1) === d ? run + 1 : 1;
    if (run > best) best = run;
    prev = d;
  }
  return { current, best, atRisk };
}

export type Quest = {
  id: string;
  label: string;
  done: number;
  target: number;
  unit: string;
  complete: boolean;
};

export const QUEST_TARGETS = { workoutDays: 3, sets: 30, mealDays: 3, prs: 1 } as const;
const MEAL_ADHERENCE = 0.9;

/** 기준일(포함)부터 7일 창의 주간 퀘스트. */
export function weeklyQuests(notes: DailyNote[], today: string, prs: PREvent[]): Quest[] {
  const start = shiftDate(today, -6);
  const inWindow = (d: string) => d >= start && d <= today;
  let workoutDays = 0;
  let sets = 0;
  let mealDays = 0;
  for (const n of notes) {
    if (!inWindow(n.date)) continue;
    let daySets = 0;
    let planned = 0;
    let eaten = 0;
    for (const b of n.blocks) {
      if (b.kind === "workout") daySets += b.logs.length;
      else if (b.kind === "meal") {
        planned += b.plan.kcal;
        if (b.eatenAt) eaten += b.plan.kcal;
      }
    }
    sets += daySets;
    if (daySets > 0) workoutDays++;
    if (planned > 0 && eaten >= planned * MEAL_ADHERENCE) mealDays++;
  }
  const weekPrs = prs.filter((p) => inWindow(p.date)).length;
  const q = (id: string, label: string, done: number, target: number, unit: string): Quest => ({
    id,
    label,
    done,
    target,
    unit,
    complete: done >= target,
  });
  return [
    q("days", "이번 주 3일 운동하기", workoutDays, QUEST_TARGETS.workoutDays, "일"),
    q("sets", "완료 세트 30개 채우기", sets, QUEST_TARGETS.sets, "세트"),
    q("meals", "식단 계획 90% 이상 지킨 날 3일", mealDays, QUEST_TARGETS.mealDays, "일"),
    q("pr", "신기록 1회 달성", weekPrs, QUEST_TARGETS.prs, "번"),
  ];
}

export const XP = { perSet: 1, perActiveDay: 10, perPR: 25 } as const;

export type Level = { xp: number; level: number; into: number; need: number };

/** 레벨 L 에 필요한 누적 XP = 50 x (L-1)^2. */
export function calcLevel(notes: DailyNote[], prs: PREvent[]): Level {
  let sets = 0;
  for (const n of notes) for (const b of n.blocks) if (b.kind === "workout") sets += b.logs.length;
  const xp = sets * XP.perSet + activeDates(notes).size * XP.perActiveDay + prs.length * XP.perPR;
  const level = Math.floor(Math.sqrt(xp / 50)) + 1;
  const floor = 50 * (level - 1) ** 2;
  const next = 50 * level ** 2;
  return { xp, level, into: xp - floor, need: next - floor };
}

export type GameState = {
  streak: ReturnType<typeof calcStreak>;
  quests: Quest[];
  level: Level;
  todayPRs: PREvent[];
  weekPRs: PREvent[];
};

/** notesAsc: 오늘 노트(현재 편집 상태)를 포함한 모든 노트, 오래된 순. */
export function buildGameState(notesAsc: DailyNote[], today: string): GameState {
  const prs = findPRs(notesAsc);
  const start = shiftDate(today, -6);
  return {
    streak: calcStreak(activeDates(notesAsc), today),
    quests: weeklyQuests(notesAsc, today, prs),
    level: calcLevel(notesAsc, prs),
    todayPRs: prs.filter((p) => p.date === today),
    weekPRs: prs.filter((p) => p.date >= start && p.date <= today),
  };
}

/** 저장된 노트들 중 현재 편집 중인 날짜의 노트를 최신 상태로 바꿔 끼운다. */
export function withCurrent(stored: DailyNote[], current: DailyNote): DailyNote[] {
  const rest = stored.filter((n) => n.date !== current.date);
  const all = current.blocks.length > 0 ? [...rest, current] : rest;
  return all.sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0));
}

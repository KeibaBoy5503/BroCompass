import type { Block } from "./types";

export type Summary = {
  plannedKcal: number;
  eatenKcal: number;
  plannedProteinG: number;
  eatenProteinG: number;
  plannedSets: number;
  doneSets: number;
  volumePlanned: number; // sets x reps x kg
  volumeDone: number;
  plannedLoad: number; // 세션 부하 분 x RPE (AU)
  doneLoad: number;
};

export function summarize(blocks: Block[]): Summary {
  const s: Summary = {
    plannedKcal: 0,
    eatenKcal: 0,
    plannedProteinG: 0,
    eatenProteinG: 0,
    plannedSets: 0,
    doneSets: 0,
    volumePlanned: 0,
    volumeDone: 0,
    plannedLoad: 0,
    doneLoad: 0,
  };
  for (const b of blocks) {
    if (b.kind === "meal") {
      s.plannedKcal += b.plan.kcal;
      s.plannedProteinG += b.plan.proteinG;
      if (b.eatenAt) {
        s.eatenKcal += b.plan.kcal;
        s.eatenProteinG += b.plan.proteinG;
      }
    } else if (b.kind === "session") {
      const load = b.plan.minutes * b.plan.rpe;
      s.plannedLoad += load;
      if (b.doneAt) s.doneLoad += load;
    } else if (b.kind === "workout") {
      s.plannedSets += b.plan.sets;
      s.doneSets += b.logs.length;
      s.volumePlanned += b.plan.reps * b.plan.weightKg * b.plan.sets;
      // 달성 볼륨은 세트별 실제 횟수 x 실제 중량 (없으면 플랜 값)
      for (const l of b.logs) {
        s.volumeDone += (l.reps ?? b.plan.reps) * (l.weightKg ?? b.plan.weightKg);
      }
    }
  }
  return s;
}

export const pct = (done: number, planned: number) =>
  planned > 0 ? Math.min(Math.round((done / planned) * 100), 100) : 0;

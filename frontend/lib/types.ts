// 플랜(목표)과 실제 수행(기록)을 분리한 블럭 모델.
// db/schema.sql 의 plan_blocks / actual_logs 와 1:1 대응한다.

export type WorkoutPlan = {
  sets: number;
  reps: number;
  weightKg: number;
};

export type MealPlan = {
  kcal: number;
  proteinG: number;
  carbG: number;
  fatG: number;
};

export type SetLog = {
  setIndex: number; // 0부터
  completedAt: number;
  // 실제 수행값. 이전 버전에서 저장된 기록에는 없을 수 있으며, 그 경우 플랜 값으로 간주한다.
  reps?: number;
  weightKg?: number;
};

type Base = {
  id: string;
  title: string;
};

export type WorkoutBlock = Base & {
  kind: "workout";
  plan: WorkoutPlan;
  logs: SetLog[]; // 완료한 세트
};

export type MealBlock = Base & {
  kind: "meal";
  plan: MealPlan;
  eatenAt: number | null; // null 이면 아직 안 먹음
};

export type SessionPlan = {
  minutes: number;
  rpe: number; // 운동 자각도 1~10 (세션 RPE)
};

/** 격투기·유산소 같은 시간 기반 훈련. 부하 = 분 x RPE (AU). */
export type SessionBlock = Base & {
  kind: "session";
  plan: SessionPlan;
  doneAt: number | null; // null 이면 아직 안 함
};

export type TextBlock = Base & {
  kind: "text";
};

export type Block = WorkoutBlock | MealBlock | SessionBlock | TextBlock;

export type DailyNote = {
  date: string; // YYYY-MM-DD
  blocks: Block[];
  updatedAt: number; // 마지막 수정 시각(ms). 기기 간 충돌 시 최신 값이 이긴다. 0 = 미기록(구버전)
};

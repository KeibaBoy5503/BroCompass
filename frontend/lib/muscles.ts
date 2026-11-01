// 근육군 분류와 주간 세트 집계. 규칙은 backend/insights.py 의 _MUSCLE_RULES 와 같은 순서·같은 키워드를 쓴다
// (먼저 나온 규칙이 우선). 한쪽을 고치면 다른 쪽도 맞춰야 한다.

import { shiftDate } from "./date";
import type { DailyNote } from "./types";

export const MUSCLES = [
  { key: "chest", label: "가슴" },
  { key: "back", label: "등" },
  { key: "shoulders_front", label: "전면 삼각근" },
  { key: "shoulders_side", label: "측면 삼각근" },
  { key: "shoulders_rear", label: "후면 삼각근" },
  { key: "biceps", label: "이두" },
  { key: "triceps", label: "삼두" },
  { key: "quads", label: "대퇴사두" },
  { key: "hamstrings", label: "햄스트링" },
  { key: "glutes", label: "둔근" },
  { key: "calves", label: "종아리" },
  { key: "abs", label: "복근" },
] as const;

export type MuscleKey = (typeof MUSCLES)[number]["key"];

/** 주간 세트 기준 (백엔드 휴리스틱과 동일). */
export const WEEKLY_SETS_TARGET = 10;

const RULES: [MuscleKey, string[]][] = [
  ["shoulders_rear", ["리어델트", "후면삼각", "페이스풀", "facepull", "reversefly", "리버스플라이", "벤트오버레이즈", "reardelt", "リアデルト", "リアレイズ", "フェイスプル", "リバースフライ", "後部三角筋", "リアーデルト", "rearlateral"]],
  ["shoulders_side", ["사이드레터럴", "레터럴레이즈", "사레레", "lateralraise", "sidelateral", "측면삼각", "레터럴", "래터럴", "라터럴", "lateral", "사이드래터럴", "사이드레이즈", "sideraise", "サイドレイズ", "ラテラルレイズ", "サイドラテラル", "側部三角筋"]],
  ["shoulders_front", ["숄더프레스", "오버헤드프레스", "밀리터리", "ohp", "overheadpress", "shoulderpress", "프론트레이즈", "frontraise", "아놀드", "ショルダープレス", "オーバーヘッドプレス", "ミリタリープレス", "フロントレイズ", "アーノルド", "숄더프래스"]],
  ["hamstrings", ["레그컬", "legcurl", "루마니안", "romanian", "rdl", "굿모닝", "햄스트링", "스티프레그", "レッグカール", "ルーマニアンデッドリフト", "ハムストリング", "ハムストリングス"]],
  ["quads", ["스쿼트", "squat", "레그프레스", "legpress", "런지", "lunge", "레그익스텐션", "legextension", "대퇴사두", "스쿼드", "스콰트", "스퀏", "スクワット", "レッグプレス", "ランジ", "レッグエクステンション", "大腿四頭筋", "hacksquat", "핵스쿼트"]],
  ["glutes", ["힙쓰러스트", "hipthrust", "글루트", "glute", "ヒップスラスト", "グルート", "臀筋", "힙쓰러스", "힙트러스트"]],
  ["calves", ["카프", "calf", "종아리", "カーフレイズ", "ふくらはぎ"]],
  ["triceps", ["푸쉬다운", "푸시다운", "pushdown", "트라이셉", "tricep", "스컬크러셔", "skullcrusher", "삼두", "딥스", "dips", "プッシュダウン", "トライセップ", "スカルクラッシャー", "ディップス", "三頭筋", "フレンチプレス", "프렌치프레스", "frenchpress", "킥백", "kickback", "キックバック"]],
  ["biceps", ["바벨컬", "덤벨컬", "해머컬", "컬", "curl", "이두", "바이셉", "bicep", "カール", "二頭筋", "프리처컬", "preachercurl", "プリーチャーカール"]],
  ["chest", ["벤치프레스", "벤치", "bench", "체스트", "인클라인프레스", "inclinepress", "덤벨프레스", "dumbbellpress", "가슴", "푸쉬업", "푸시업", "pushup", "펙덱", "pecdeck", "플라이", "fly", "크로스오버", "ベンチプレス", "ベンチ", "インクラインプレス", "ダンベルプレス", "チェスト", "腕立て", "プッシュアップ", "ペックデック", "フライ", "ケーブルクロスオーバー", "胸", "벤치프래스", "벤치푸레스", "체스트프레스", "chestpress"]],
  ["back", ["풀업", "턱걸이", "pullup", "chinup", "랫풀", "latpull", "풀다운", "pulldown", "로우", "row", "데드리프트", "deadlift", "懸垂", "チンニング", "ラットプルダウン", "プルダウン", "ロウ", "ローイング", "ベントオーバーロー", "デッドリフト", "背中", "랫플다운", "래풀다운", "랫풀다운", "풀다은", "데드리프", "pullover", "풀오버", "시티드로우", "シーテッドロー"]],
  ["abs", ["크런치", "crunch", "플랭크", "plank", "레그레이즈", "legraise", "복근", "싯업", "situp", "クランチ", "プランク", "レッグレイズ", "腹筋", "シットアップ", "アブローラー", "abwheel", "앱휠", "행잉레그레이즈"]],
];

const norm = (s: string) => s.toLowerCase().replace(/[^a-z0-9가-힣\u3040-\u30ff\u4e00-\u9fa5ー]/g, "");

/** 이 길이 이상인 키워드만 오타(글자 1개 차이)를 허용한다. 짧은 단어는 오탐이 많다. */
export const FUZZY_MIN_LEN = 5;

/** 편집 거리(삽입·삭제·교체)가 1 이하인가. */
function distLe1(a: string, b: string): boolean {
  if (a === b) return true;
  if (Math.abs(a.length - b.length) > 1) return false;
  let i = 0;
  while (i < Math.min(a.length, b.length) && a[i] === b[i]) i++;
  if (a.length === b.length) return a.slice(i + 1) === b.slice(i + 1);
  const [short, long] = a.length < b.length ? [a, b] : [b, a];
  return short.slice(i) === long.slice(i + 1);
}

function near(n: string, key: string): boolean {
  if (key.length < FUZZY_MIN_LEN) return false;
  for (const size of [key.length - 1, key.length, key.length + 1]) {
    for (let i = 0; i + size <= n.length; i++) if (distLe1(n.slice(i, i + size), key)) return true;
  }
  return false;
}

/** 운동 이름 -> 근육군. 먼저 정확히 포함되는 키워드를 찾고, 없을 때만 오타를 허용해 다시 찾는다. */
export function classify(title: string): MuscleKey | null {
  const n = norm(title);
  for (const [muscle, keys] of RULES) if (keys.some((k) => n.includes(k))) return muscle;
  for (const [muscle, keys] of RULES) if (keys.some((k) => near(n, k))) return muscle;
  return null;
}

/** 기준일(포함) 7일 창에서 근육군별 완료 세트 수. 분류되지 않은 운동은 unclassified 로 센다. */
export function weeklySetsByMuscle(
  notes: DailyNote[],
  today: string
): { sets: Record<MuscleKey, number>; unclassified: number } {
  const start = shiftDate(today, -6);
  const sets = Object.fromEntries(MUSCLES.map((m) => [m.key, 0])) as Record<MuscleKey, number>;
  let unclassified = 0;
  for (const n of notes) {
    if (n.date < start || n.date > today) continue;
    for (const b of n.blocks) {
      if (b.kind !== "workout" || b.logs.length === 0) continue;
      const m = classify(b.title);
      if (m) sets[m] += b.logs.length;
      else unclassified += b.logs.length;
    }
  }
  return { sets, unclassified };
}

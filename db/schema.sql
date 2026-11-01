-- BroCompass DB 스키마 (PostgreSQL / Supabase)
-- 핵심 설계: '플랜(목표)'과 '실제 수행(기록)'을 분리해 계획 대비 달성률을 계산한다.

create extension if not exists "pgcrypto";

-- 사용자 프로필 (Supabase auth.users 와 1:1 연결 가능)
create table profiles (
  id            uuid primary key default gen_random_uuid(),
  sex           text not null check (sex in ('male', 'female')),
  birth_year    int,
  height_cm     numeric(5,1),
  weight_kg     numeric(5,1),
  body_fat_pct  numeric(4,1),
  activity      text not null default 'moderate',
  goal          text not null default 'maintain' check (goal in ('cut', 'maintain', 'bulk')),
  body_type     text not null default 'mesomorph',
  created_at    timestamptz not null default now()
);

-- 하루 단위 노트
create table daily_notes (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null references profiles(id) on delete cascade,
  note_date   date not null,
  memo        text,
  unique (user_id, note_date)
);

-- 블럭 종류: 운동 / 식단 / 자유 메모
create type block_kind as enum ('workout', 'meal', 'text');

-- ① 플랜 블럭 (목표) -------------------------------------------------
create table plan_blocks (
  id            uuid primary key default gen_random_uuid(),
  note_id       uuid not null references daily_notes(id) on delete cascade,
  kind          block_kind not null,
  position      int not null,                 -- 드래그 앤 드롭 순서
  title         text not null,                -- 예: '벤치프레스', '닭가슴살'
  -- 운동 플랜
  planned_sets  int,
  planned_reps  int,
  planned_weight_kg numeric(5,1),
  -- 식단 플랜
  planned_kcal    numeric(6,1),
  planned_carb_g  numeric(6,1),
  planned_protein_g numeric(6,1),
  planned_fat_g   numeric(6,1),
  created_at    timestamptz not null default now()
);
create index on plan_blocks (note_id, position);

-- ② 실제 수행 기록 (세트/섭취 단위) ---------------------------------
create table actual_logs (
  id            uuid primary key default gen_random_uuid(),
  plan_block_id uuid references plan_blocks(id) on delete set null,  -- 플랜 없이 즉흥 기록도 허용
  note_id       uuid not null references daily_notes(id) on delete cascade,
  kind          block_kind not null,
  set_index     int,                          -- 운동: 몇 번째 세트
  reps          int,
  weight_kg     numeric(5,1),
  rpe           numeric(3,1),                 -- 운동 강도(선택)
  kcal          numeric(6,1),
  carb_g        numeric(6,1),
  protein_g     numeric(6,1),
  fat_g         numeric(6,1),
  photo_url     text,                         -- Phase 3: 식단 사진
  completed_at  timestamptz not null default now()
);
create index on actual_logs (note_id);
create index on actual_logs (plan_block_id);

-- 플랜 대비 달성률 뷰
create view v_plan_progress as
select
  p.id               as plan_block_id,
  p.note_id,
  p.title,
  p.kind,
  p.planned_sets,
  count(a.id)        as done_sets,
  p.planned_kcal,
  coalesce(sum(a.kcal), 0) as eaten_kcal
from plan_blocks p
left join actual_logs a on a.plan_block_id = p.id
group by p.id;

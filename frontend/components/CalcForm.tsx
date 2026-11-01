"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { haptic } from "@/lib/haptic";
import type { CalcInput } from "@/lib/api";
import { useT } from "@/lib/i18n";

const ACTIVITY = [
  ["sedentary", "거의 안 함"],
  ["light", "주 1~3회"],
  ["moderate", "주 3~5회"],
  ["active", "주 6~7회"],
  ["very_active", "하루 2회 / MMA 병행"],
] as const;

const GOALS = [
  ["cut", "감량"],
  ["maintain", "유지"],
  ["bulk", "증량"],
] as const;

const BODY_TYPES = [
  ["ectomorph", "마른 체질"],
  ["mesomorph", "보통 체형"],
  ["endomorph", "살 잘 찌는"],
] as const;

const field =
  "w-full rounded-lg border border-line bg-panel px-3 py-3 text-zinc-100 outline-none focus:border-neon focus:shadow-neon transition";

function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: readonly (readonly [T, string])[];
  onChange: (v: T) => void;
}) {
  const t = useT();
  return (
    <div className="grid auto-cols-fr grid-flow-col gap-2">
      {options.map(([v, label]) => (
        <motion.button
          key={v}
          type="button"
          whileTap={{ scale: 0.94 }}
          onClick={() => {
            haptic(10);
            onChange(v);
          }}
          className={`rounded-lg border px-2 py-3 text-sm transition ${
            value === v
              ? "border-neon bg-neon/10 text-neon shadow-neon"
              : "border-line bg-panel text-zinc-400"
          }`}
        >
          {t(label)}
        </motion.button>
      ))}
    </div>
  );
}

export default function CalcForm({
  onSubmit,
  loading,
}: {
  onSubmit: (v: CalcInput) => void;
  loading: boolean;
}) {
  const t = useT();
  const [sex, setSex] = useState<CalcInput["sex"]>("male");
  const [age, setAge] = useState("28");
  const [height, setHeight] = useState("175");
  const [weight, setWeight] = useState("75");
  const [bodyFat, setBodyFat] = useState("");
  const [activity, setActivity] = useState<CalcInput["activity"]>("moderate");
  const [goal, setGoal] = useState<CalcInput["goal"]>("maintain");
  const [bodyType, setBodyType] = useState<CalcInput["body_type"]>("mesomorph");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    haptic([20, 30, 20]);
    onSubmit({
      sex,
      age: Number(age),
      height_cm: Number(height),
      weight_kg: Number(weight),
      activity,
      goal,
      body_type: bodyType,
      ...(bodyFat ? { body_fat_pct: Number(bodyFat) } : {}),
    });
  };

  return (
    <form onSubmit={submit} className="space-y-5">
      <Label text={t("성별")}>
        <Segmented
          value={sex}
          onChange={setSex}
          options={[["male", "남성"], ["female", "여성"]]}
        />
      </Label>

      <div className="grid grid-cols-3 gap-3">
        <Label text={t("나이")}>
          <input className={field} inputMode="numeric" value={age} onChange={(e) => setAge(e.target.value)} />
        </Label>
        <Label text={t("키(cm)")}>
          <input className={field} inputMode="decimal" value={height} onChange={(e) => setHeight(e.target.value)} />
        </Label>
        <Label text={t("체중(kg)")}>
          <input className={field} inputMode="decimal" value={weight} onChange={(e) => setWeight(e.target.value)} />
        </Label>
      </div>

      <Label text={t("체지방률 % (선택 · 입력 시 Katch-McArdle 사용)")}>
        <input className={field} inputMode="decimal" placeholder={t("예: 15")} value={bodyFat} onChange={(e) => setBodyFat(e.target.value)} />
      </Label>

      <Label text={t("활동량")}>
        <select
          className={field}
          value={activity}
          onChange={(e) => setActivity(e.target.value as CalcInput["activity"])}
        >
          {ACTIVITY.map(([v, l]) => (
            <option key={v} value={v}>{t(l)}</option>
          ))}
        </select>
      </Label>

      <Label text={t("목표")}>
        <Segmented value={goal} onChange={setGoal} options={GOALS} />
      </Label>

      <Label text={t("체질")}>
        <Segmented value={bodyType} onChange={setBodyType} options={BODY_TYPES} />
      </Label>

      <motion.button
        type="submit"
        disabled={loading}
        whileTap={{ scale: 0.97 }}
        className="w-full rounded-lg bg-neon py-4 font-bold text-black shadow-neon disabled:opacity-50"
      >
        {loading ? t("계산 중...") : t("계산하기")}
      </motion.button>
    </form>
  );
}

function Label({ text, children }: { text: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1.5 block font-mono text-xs uppercase tracking-wider text-zinc-500">
        {text}
      </span>
      {children}
    </label>
  );
}

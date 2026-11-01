"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { haptic } from "@/lib/haptic";
import { compressImage } from "@/lib/image";
import { analyzeMeal } from "@/lib/mealApi";
import {
  SCALES,
  applyScale,
  kcalFromMacros,
  kcalMismatch,
  macroKcal,
  rowsToBlocks,
  scaledGrams,
  toDraftRows,
  totalKcal,
  type DraftRow,
} from "@/lib/mealItems";
import type { Block } from "@/lib/types";
import { useLang, useT } from "@/lib/i18n";

type Phase = "idle" | "analyzing" | "review";

const input =
  "w-full rounded-lg border border-line bg-ink px-2.5 py-2 text-zinc-100 outline-none focus:border-neon";

function NumField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  const t = useT();
  return (
    <label className="block">
      <span className="mb-1 block font-mono text-[10px] uppercase tracking-wider text-zinc-500">
        {t(label)}
      </span>
      <input
        className={`${input} text-center font-mono text-sm`}
        inputMode="decimal"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}

export default function MealPhotoButton({ onAdd }: { onAdd: (blocks: Block[]) => void }) {
  const { t, lang } = useLang();
  const [phase, setPhase] = useState<Phase>("idle");
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<DraftRow[]>([]);
  const [note, setNote] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [eaten, setEaten] = useState(true);
  const [hint, setHint] = useState("");

  const fileRef = useRef<HTMLInputElement>(null);
  const imgRef = useRef<{ base64: string; mime: string } | null>(null); // 힌트로 다시 분석할 때 재사용
  const abortRef = useRef<AbortController | null>(null);

  const blocks = useMemo(() => rowsToBlocks(rows, eaten), [rows, eaten]);

  const close = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setPhase("idle");
    setRows([]);
    setNote("");
    setWarnings([]);
    setHint("");
    imgRef.current = null;
  };

  // 페이지를 떠날 때 진행 중인 요청 취소
  useEffect(() => () => abortRef.current?.abort(), []);

  // Esc 로 닫기
  useEffect(() => {
    if (phase === "idle") return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && close();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [phase]);

  /** file 이 있으면 새 사진을 줄여서 분석하고, null 이면 직전 사진을 힌트와 함께 다시 분석한다. */
  const analyze = async (file: File | null, hintText: string) => {
    if (!file && !imgRef.current) return;
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    setError(null);
    setPhase("analyzing");
    try {
      let img = imgRef.current;
      if (file) {
        img = await compressImage(file);
        if (ctrl.signal.aborted) return;
        imgRef.current = img;
      }
      if (!img) return;
      const res = await analyzeMeal(img.base64, img.mime, ctrl.signal, hintText.trim() || undefined, lang);
      if (ctrl.signal.aborted) return;
      if (res.items.length === 0) {
        setError(res.note || t("사진에서 음식을 찾지 못했어요. 다른 사진으로 시도해 보세요."));
        setPhase("idle");
        return;
      }
      setRows(toDraftRows(res.items));
      setNote(res.note);
      setWarnings(res.warnings);
      setEaten(true);
      setPhase("review");
      haptic(30);
    } catch (e) {
      if (ctrl.signal.aborted) return;
      setError(t(e instanceof Error ? e.message : "알 수 없는 오류가 발생했어요."));
      setPhase("idle");
    }
  };

  const patch = (key: string, p: Partial<DraftRow>) =>
    setRows((rs) => rs.map((r) => (r.key === key ? { ...r, ...p } : r)));

  const confirm = () => {
    if (blocks.length === 0) return;
    haptic([20, 30, 40]);
    onAdd(blocks);
    close();
  };

  return (
    <div>
      <input
        ref={fileRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          e.target.value = ""; // 같은 사진을 다시 골라도 change 가 발생하도록 초기화
          if (f) {
            setHint("");
            void analyze(f, "");
          }
        }}
      />
      <motion.button
        type="button"
        whileTap={{ scale: 0.96 }}
        disabled={phase !== "idle"}
        onClick={() => {
          haptic(10);
          fileRef.current?.click();
        }}
        className="rounded-xl border border-line bg-panel px-4 py-2.5 font-mono text-xs text-zinc-400 transition hover:text-neon disabled:opacity-50"
      >
        {t("📷 사진으로 식단 추가")}
      </motion.button>
      {error && (
        <p role="alert" className="mt-2 max-w-xs font-mono text-xs text-red-300">
          {error}
        </p>
      )}

      <AnimatePresence>
        {phase !== "idle" && (
          <motion.div
            className="fixed inset-0 z-50 flex items-end justify-center bg-black/70 md:items-center"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={(e) => e.target === e.currentTarget && phase === "review" && close()}
          >
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label={t("식단 사진 분석 결과")}
              initial={{ y: 40, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 40, opacity: 0 }}
              className="max-h-[88vh] w-full max-w-md overflow-y-auto rounded-t-2xl border border-line bg-panel p-4 md:rounded-2xl"
            >
              {phase === "analyzing" ? (
                <div className="py-8 text-center">
                  <motion.div
                    className="mx-auto mb-4 h-10 w-10 rounded-full border-2 border-line border-t-neon"
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 0.9, ease: "linear" }}
                  />
                  <p className="font-semibold">{t("사진을 분석하는 중…")}</p>
                  <p className="mt-1 font-mono text-xs text-zinc-500">
                    {t("최대 1분 정도 걸릴 수 있어요. 사진은 AI 분석 서버로 전송돼요.")}
                  </p>
                  <button
                    type="button"
                    onClick={close}
                    className="mt-5 rounded-lg border border-line px-4 py-2 font-mono text-xs text-zinc-400"
                  >
                    {t("취소")}
                  </button>
                </div>
              ) : (
                <>
                  <h2 className="font-semibold">
                    {t("분석 결과")} <span className="font-mono text-xs text-zinc-500">{t("AI 추정")}</span>
                  </h2>
                  {note && <p className="mt-1 text-sm text-zinc-400">{note}</p>}
                  {warnings.length > 0 && (
                    <ul className="mt-2 space-y-1 rounded-lg border border-amber-400/30 bg-amber-400/5 p-2 text-xs text-amber-300">
                      {warnings.map((w, i) => (
                        <li key={i}>⚠ {w}</li>
                      ))}
                    </ul>
                  )}

                  <ul className="mt-3 space-y-3">
                    {rows.map((r) => (
                      <li key={r.key} className="rounded-xl border border-line bg-ink p-3">
                        <div className="flex gap-2">
                          <input
                            className={input}
                            aria-label={t("음식 이름")}
                            maxLength={60}
                            value={r.name}
                            onChange={(e) => patch(r.key, { name: e.target.value })}
                          />
                          <button
                            type="button"
                            aria-label={t("이 항목 삭제")}
                            onClick={() => setRows((rs) => rs.filter((x) => x.key !== r.key))}
                            className="px-2 text-zinc-600 hover:text-red-400"
                          >
                            ✕
                          </button>
                        </div>
                        {(r.confidence === "low" || scaledGrams(r) !== null) && (
                          <div className="mt-2 flex flex-wrap items-center gap-2">
                            {r.confidence === "low" && (
                              <span className="rounded border border-amber-400/40 px-1.5 py-0.5 font-mono text-[10px] text-amber-300">
                                {t("AI 확신 낮음")}
                              </span>
                            )}
                            {scaledGrams(r) !== null && (
                              <span className="font-mono text-[10px] text-zinc-500">
                                {t("약 {g}g 기준", { g: scaledGrams(r) ?? "" })}
                              </span>
                            )}
                          </div>
                        )}
                        <div className="mt-2 flex flex-wrap items-center gap-1" role="group" aria-label={t("양 조절")}>
                          <span className="mr-1 font-mono text-[10px] text-zinc-500">{t("양")}</span>
                          {SCALES.map((sc) => (
                            <button
                              key={sc}
                              type="button"
                              aria-pressed={r.scale === sc}
                              onClick={() => {
                                haptic(8);
                                setRows((rs) => rs.map((x) => (x.key === r.key ? applyScale(x, sc) : x)));
                              }}
                              className={`rounded-md border px-2 py-1 font-mono text-[11px] transition ${
                                r.scale === sc
                                  ? "border-neon bg-neon/10 text-neon"
                                  : "border-line text-zinc-400 hover:text-zinc-200"
                              }`}
                            >
                              {sc}×
                            </button>
                          ))}
                        </div>
                        <div className="mt-2 grid grid-cols-4 gap-2">
                          <NumField label="kcal" value={r.kcal} onChange={(v) => patch(r.key, { kcal: v, scale: null })} />
                          <NumField label="단백질" value={r.protein} onChange={(v) => patch(r.key, { protein: v, scale: null })} />
                          <NumField label="탄수" value={r.carb} onChange={(v) => patch(r.key, { carb: v, scale: null })} />
                          <NumField label="지방" value={r.fat} onChange={(v) => patch(r.key, { fat: v, scale: null })} />
                        </div>
                        {kcalMismatch(r) && (
                          <button
                            type="button"
                            onClick={() => setRows((rs) => rs.map((x) => (x.key === r.key ? kcalFromMacros(x) : x)))}
                            className="mt-2 w-full rounded-lg border border-amber-400/30 px-2 py-1.5 text-left font-mono text-[11px] text-amber-300 hover:bg-amber-400/5"
                          >
                            {t("칼로리를 탄단지 기준 {n}kcal로 맞추기", { n: Math.round(macroKcal(r)) })}
                          </button>
                        )}
                      </li>
                    ))}
                  </ul>

                  <div className="mt-3">
                    <div className="flex gap-2">
                      <input
                        className={input}
                        aria-label={t("음식 힌트")}
                        maxLength={80}
                        placeholder={t("음식을 잘못 알아봤다면 힌트 입력 (예: 닭가슴살 샐러드)")}
                        value={hint}
                        onChange={(e) => setHint(e.target.value)}
                      />
                      <button
                        type="button"
                        disabled={!hint.trim()}
                        onClick={() => void analyze(null, hint)}
                        className="shrink-0 rounded-lg border border-line px-3 font-mono text-xs text-zinc-300 disabled:opacity-40"
                      >
                        {t("다시 분석")}
                      </button>
                    </div>
                    <p className="mt-1 text-[10px] text-zinc-600">{t("다시 분석하면 지금까지 고친 값은 사라져요.")}</p>
                  </div>

                  <p className="mt-3 text-right font-mono text-xs text-zinc-400">
                    {t("합계")} <b className="text-neon">{Math.round(totalKcal(rows))}</b> kcal
                  </p>

                  <label className="mt-3 flex items-center gap-2 text-sm text-zinc-300">
                    <input
                      type="checkbox"
                      checked={eaten}
                      onChange={(e) => setEaten(e.target.checked)}
                      className="h-4 w-4 accent-[#39FF88]"
                    />
                    {t("먹은 것으로 기록 (섭취 완료)")}
                  </label>
                  <p className="mt-2 text-[11px] leading-relaxed text-zinc-600">
                    {t("사진으로 추정한 값은 양·조리법에 따라 오차가 커요. 실제와 다르면 수정한 뒤 추가하세요.")}
                  </p>

                  <div className="mt-4 flex gap-2">
                    <button
                      type="button"
                      onClick={close}
                      className="flex-1 rounded-xl border border-line py-3 text-sm text-zinc-400"
                    >
                      {t("취소")}
                    </button>
                    <motion.button
                      type="button"
                      whileTap={{ scale: 0.97 }}
                      disabled={blocks.length === 0}
                      onClick={confirm}
                      className="flex-[2] rounded-xl bg-neon py-3 text-sm font-bold text-black shadow-neon disabled:opacity-40"
                    >
                      {t("{n}개 추가", { n: blocks.length })}
                    </motion.button>
                  </div>
                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

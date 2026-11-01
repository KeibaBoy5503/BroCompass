// 번역 순수 함수. React 에 의존하지 않아 Node 에서 바로 테스트할 수 있다.
import { EN, JA } from "./messages";

export type Lang = "ko" | "ja" | "en";
export const LANGS: { code: Lang; label: string }[] = [
  { code: "ko", label: "한국어" },
  { code: "ja", label: "日本語" },
  { code: "en", label: "English" },
];

export const STORAGE_KEY = "brocompass:lang";
export const isLang = (v: unknown): v is Lang => v === "ko" || v === "ja" || v === "en";

/** 저장된 값이 없을 때 브라우저 언어로 정한다 (ja* -> 일본어, en* -> 영어, 그 외 한국어). */
export function detectLang(browserLang: string | undefined): Lang {
  const l = (browserLang ?? "").toLowerCase();
  if (l.startsWith("ja")) return "ja";
  if (l.startsWith("en")) return "en";
  return "ko";
}

export type Vars = Record<string, string | number>;

/** 순수 함수: 사전에서 문장을 찾고 {이름} 자리를 값으로 바꾼다. */
export function translate(lang: Lang, key: string, vars?: Vars): string {
  const dict = lang === "ja" ? JA : lang === "en" ? EN : null;
  const text = dict?.[key] ?? key;
  return vars ? text.replace(/\{(\w+)\}/g, (m, k) => (k in vars ? String(vars[k]) : m)) : text;
}


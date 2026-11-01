"use client";

// 가벼운 다국어(한국어·일본어·영어) 지원. 외부 라이브러리 없이 사전 한 벌로 처리한다.
// 키는 한국어 원문이다: t("오늘") -> ko: 오늘 / ja: 今日 / en: Today.
// 사전(messages.ts)에 없는 문장은 한국어 원문 그대로 보인다 (번역이 빠져도 화면이 깨지지 않는다).

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { STORAGE_KEY, detectLang, isLang, translate, type Lang, type Vars } from "./translate";

export { LANGS } from "./translate";
export type { Lang } from "./translate";

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (key: string, vars?: Vars) => string };
const LangContext = createContext<Ctx>({ lang: "ko", setLang: () => {}, t: (k, v) => translate("ko", k, v) });

export function LangProvider({ children }: { children: React.ReactNode }) {
  // 서버 렌더와 첫 클라이언트 렌더를 같게 두려고 한국어로 시작하고, 마운트 뒤에 저장된 언어로 바꾼다.
  const [lang, setLangState] = useState<Lang>("ko");

  useEffect(() => {
    let saved: string | null = null;
    try {
      saved = localStorage.getItem(STORAGE_KEY);
    } catch {
      /* 무시 */
    }
    setLangState(isLang(saved) ? saved : detectLang(navigator.language));
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(STORAGE_KEY, l);
    } catch {
      /* 무시 */
    }
  }, []);

  const value = useMemo<Ctx>(() => ({ lang, setLang, t: (k, v) => translate(lang, k, v) }), [lang, setLang]);
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);
export const useT = () => useContext(LangContext).t;

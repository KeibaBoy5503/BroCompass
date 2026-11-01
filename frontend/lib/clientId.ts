// 로그인 없이 사용자별로 노트를 나누기 위한 브라우저 고유 ID.
// 이 ID 를 아는 사람만 해당 노트를 읽을 수 있으므로 '비밀 링크' 수준의 분리이며, 정식 인증은 아니다.
// localStorage 에 저장해 새로고침해도 유지한다. 저장소를 못 쓰는 환경에서는 탭이 열려 있는 동안만 유지된다.

const KEY = "brocompass:clientId";
export const CLIENT_ID_RE = /^[A-Za-z0-9_-]{16,64}$/;

let memoryId: string | null = null;

export function newClientId(): string {
  const c = typeof crypto !== "undefined" ? crypto : undefined;
  if (c?.randomUUID) return c.randomUUID();
  const bytes = new Uint8Array(16);
  if (c?.getRandomValues) c.getRandomValues(bytes);
  else for (let i = 0; i < bytes.length; i++) bytes[i] = Math.floor(Math.random() * 256);
  return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
}

export function getClientId(): string {
  try {
    const saved = localStorage.getItem(KEY);
    if (saved && CLIENT_ID_RE.test(saved)) return saved;
    const id = newClientId();
    localStorage.setItem(KEY, id);
    return id;
  } catch {
    return (memoryId ??= newClientId());
  }
}

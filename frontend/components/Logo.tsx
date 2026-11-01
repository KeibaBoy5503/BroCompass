export default function Logo({ size = 40 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      stroke="#39FF88"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      style={{ filter: "drop-shadow(0 0 6px rgba(57,255,136,0.7))" }}
      aria-label="BroCompass"
    >
      {/* 나침반 외곽 */}
      <circle cx="32" cy="32" r="28" />
      {/* 방위 눈금 */}
      <path d="M32 4v6M32 54v6M4 32h6M54 32h6" />
      {/* 브로콜리 송이 */}
      <path d="M22 30a6 6 0 0 1 4-10 7 7 0 0 1 12 0 6 6 0 0 1 4 10 6 6 0 0 1-6 3H28a6 6 0 0 1-6-3z" />
      {/* 줄기 */}
      <path d="M32 33v11M32 40l-4-3M32 40l4-3" />
    </svg>
  );
}

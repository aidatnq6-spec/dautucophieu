/** Linh vật của trợ lý: an original round robot head of the app's own, with big eyes, a headset and an antenna tipped with a gold
 * coin (Gia Sản: wealth). Drawn in SVG with fixed colours so it reads on light and dark themes alike. */
export function Mascot({ size = 56, blink = true }: { size?: number; blink?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true" className={blink ? "ms ms-blink" : "ms"}>
      <defs>
        <radialGradient id="ms-head" cx="40%" cy="30%" r="75%"><stop offset="0" stopColor="#ffffff" /><stop offset="1" stopColor="#dbe6f7" /></radialGradient>
        <linearGradient id="ms-face" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#1f4fae" /><stop offset="1" stopColor="#163b82" /></linearGradient>
      </defs>
      {/* antenna with a gold coin */}
      <line x1="32" y1="12" x2="32" y2="5" stroke="#1f4fae" strokeWidth="2.5" strokeLinecap="round" />
      <circle cx="32" cy="5" r="4" fill="#f5b52e" stroke="#c98a10" strokeWidth="1" />
      <text x="32" y="6.8" textAnchor="middle" fontSize="5" fontWeight="700" fill="#8a5a00">₫</text>
      {/* headset band and ear cups */}
      <path d="M10 33 C10 17 54 17 54 33" fill="none" stroke="#f5b52e" strokeWidth="3.5" strokeLinecap="round" />
      <rect x="4" y="28" width="9" height="15" rx="4.5" fill="#f5b52e" stroke="#c98a10" strokeWidth="1" />
      <rect x="51" y="28" width="9" height="15" rx="4.5" fill="#f5b52e" stroke="#c98a10" strokeWidth="1" />
      {/* head */}
      <circle cx="32" cy="35" r="21" fill="url(#ms-head)" stroke="#9fb4d6" strokeWidth="1.2" />
      {/* face visor */}
      <rect x="17" y="25" width="30" height="20" rx="10" fill="url(#ms-face)" />
      {/* eyes and smile */}
      <g className="ms-eyes">
        <ellipse cx="26" cy="34" rx="3.2" ry="3.8" fill="#7ff0d0" />
        <ellipse cx="38" cy="34" rx="3.2" ry="3.8" fill="#7ff0d0" />
        <circle cx="27" cy="32.6" r="1" fill="#ffffff" />
        <circle cx="39" cy="32.6" r="1" fill="#ffffff" />
      </g>
      <path d="M28 40.5 Q32 43.5 36 40.5" fill="none" stroke="#7ff0d0" strokeWidth="1.8" strokeLinecap="round" />
      {/* cheeks and microphone */}
      <circle cx="20" cy="45" r="2.2" fill="#ffb3b3" opacity=".8" />
      <circle cx="44" cy="45" r="2.2" fill="#ffb3b3" opacity=".8" />
      <path d="M8 42 Q10 51 20 51" fill="none" stroke="#c98a10" strokeWidth="1.8" strokeLinecap="round" />
      <circle cx="21" cy="51" r="2" fill="#1f4fae" />
    </svg>
  );
}

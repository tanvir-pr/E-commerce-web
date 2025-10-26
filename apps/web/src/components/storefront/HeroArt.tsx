/** Full-bleed clinical texture + serum silhouette for the home hero. */
export function HeroArt() {
  return (
    <div className="absolute inset-0 overflow-hidden" aria-hidden="true">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_70%_40%,#d8e4de_0%,transparent_55%),radial-gradient(ellipse_at_20%_80%,#f3e6cc_0%,transparent_45%),linear-gradient(160deg,#e8eee9_0%,#f2f4f1_45%,#dfe8e3_100%)]" />
      <div
        className="absolute inset-0 opacity-[0.18] mix-blend-multiply"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
      <svg
        className="media-zoom animate-soft-zoom absolute -right-[8%] top-[8%] h-[84%] w-auto max-w-[70%] text-sage-deep/80"
        viewBox="0 0 420 640"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <ellipse cx="210" cy="590" rx="120" ry="22" fill="#5f7d70" opacity="0.12" />
        <rect x="168" y="70" width="84" height="28" rx="6" fill="#3f564c" />
        <rect x="188" y="40" width="44" height="40" rx="8" fill="#5f7d70" />
        <path
          d="M198 40 C198 18 222 12 222 40"
          stroke="#3f564c"
          strokeWidth="10"
          strokeLinecap="round"
          fill="none"
        />
        <rect x="140" y="98" width="140" height="420" rx="48" fill="#fafbf9" stroke="#5f7d70" strokeWidth="3" />
        <rect x="158" y="130" width="104" height="180" rx="28" fill="#d8e4de" opacity="0.85" />
        <path
          d="M210 330 C170 360 165 420 210 460 C255 420 250 360 210 330 Z"
          fill="#c9892e"
          opacity="0.35"
        />
        <circle cx="210" cy="390" r="36" fill="#5f7d70" opacity="0.2" />
      </svg>
      <div className="absolute inset-0" style={{ background: "var(--hero-veil)" }} />
    </div>
  );
}

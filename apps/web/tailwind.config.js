/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "var(--color-paper)",
        surface: "var(--color-surface)",
        ink: "var(--color-ink)",
        muted: "var(--color-muted)",
        line: "var(--color-line)",
        danger: "var(--color-danger)",
        ok: "var(--color-ok)",
        sage: {
          DEFAULT: "var(--color-sage)",
          soft: "var(--color-sage-soft)",
          deep: "var(--color-sage-deep)",
        },
        saffron: {
          DEFAULT: "var(--color-saffron)",
          soft: "var(--color-saffron-soft)",
        },
        brand: {
          DEFAULT: "var(--color-sage)",
          foreground: "#ffffff",
          pressed: "var(--color-sage-deep)",
        },
      },
      spacing: {
        "2xs": "4px",
        xs: "8px",
        sm: "12px",
        md: "16px",
        lg: "24px",
        xl: "32px",
        "2xl": "48px",
        "3xl": "72px",
        tap: "44px",
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "ui-sans-serif", "sans-serif"],
        display: ["var(--font-display)", "ui-serif", "Georgia", "serif"],
      },
      fontSize: {
        hero: ["clamp(2.75rem, 6vw, 4.5rem)", { lineHeight: "1.05", letterSpacing: "-0.03em" }],
        display: ["clamp(1.75rem, 3vw, 2.5rem)", { lineHeight: "1.15", letterSpacing: "-0.02em" }],
      },
      transitionTimingFunction: {
        reveal: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
      keyframes: {
        "rise-in": {
          from: { opacity: "0", transform: "translateY(18px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "soft-zoom": {
          from: { transform: "scale(1)" },
          to: { transform: "scale(1.04)" },
        },
        "press-pop": {
          "0%": { transform: "scale(1)" },
          "40%": { transform: "scale(0.96)" },
          "100%": { transform: "scale(1)" },
        },
      },
      animation: {
        "rise-in": "rise-in 700ms var(--ease-reveal) both",
        "soft-zoom": "soft-zoom 8s ease-in-out alternate infinite",
        "press-pop": "press-pop 320ms var(--ease-reveal)",
      },
    },
  },
  plugins: [],
};

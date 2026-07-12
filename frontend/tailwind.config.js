/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#080a12",
        surface: "#0e1220",
        "surface-2": "#151b2e",
        line: "rgba(255,255,255,0.09)",
        "line-strong": "rgba(255,255,255,0.16)",
        ink: "#f1f4fb",
        muted: "rgba(241,244,251,0.62)",
        faint: "rgba(241,244,251,0.4)",
        bull: "#1fdd97",
        "bull-deep": "#12b87e",
        bear: "#ff5470",
        gold: "#ffb020",
        violet: "#7c5cff",
        indigo: "#5b6bff",
        cyan: "#22d3ee",
        pink: "#f471b5",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["'Space Grotesk'", "Inter", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      borderRadius: {
        "4xl": "1.75rem",
      },
      boxShadow: {
        card: "0 1px 0 0 rgba(255,255,255,0.05) inset, 0 20px 50px -24px rgba(0,0,0,0.8)",
        lift: "0 24px 60px -20px rgba(0,0,0,0.7), 0 1px 0 0 rgba(255,255,255,0.06) inset",
        "glow-violet": "0 10px 40px -8px rgba(124,92,255,0.55)",
        "glow-bull": "0 10px 40px -10px rgba(31,221,151,0.5)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(14px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          "0%": { opacity: "0", transform: "scale(0.97)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-500px 0" },
          "100%": { backgroundPosition: "500px 0" },
        },
        float: {
          "0%,100%": { transform: "translate(0,0) scale(1)" },
          "50%": { transform: "translate(3%,4%) scale(1.08)" },
        },
        "pulse-soft": {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.55s cubic-bezier(0.22,1,0.36,1) both",
        "scale-in": "scale-in 0.4s ease both",
        shimmer: "shimmer 1.5s linear infinite",
        "float-slow": "float 22s ease-in-out infinite",
        "pulse-soft": "pulse-soft 2.4s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

/** @type {import('tailwindcss').Config} */
const token = (name) => `rgb(var(--${name}) / <alpha-value>)`;

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: ["selector", '[data-theme="dark"]'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Inter Variable"', "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
      },
      colors: {
        page: token("page"),
        surface: token("surface"),
        "surface-2": token("surface-2"),
        ink: token("ink"),
        "ink-2": token("ink-2"),
        muted: token("muted"),
        line: token("line"),
        brand: token("brand"),
        "brand-2": token("brand-2"),
        "brand-soft": token("brand-soft"),
        // fixed (un-themed) gradient so white text keeps contrast in both modes
        "grad-a": "#4f46e5",
        "grad-b": "#7c3aed",
        series: token("series-1"),
        track: token("track"),
        good: token("good"),
        warning: token("warning"),
        serious: token("serious"),
        critical: token("critical"),
      },
      boxShadow: {
        card: "0 1px 2px rgb(15 23 42 / 0.04), 0 1px 3px rgb(15 23 42 / 0.06)",
        pop: "0 10px 30px -10px rgb(15 23 42 / 0.25)",
      },
      keyframes: {
        "fade-in": { from: { opacity: 0, transform: "translateY(4px)" }, to: { opacity: 1, transform: "none" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: {
        "fade-in": "fade-in 200ms ease-out both",
        shimmer: "shimmer 1.4s infinite",
      },
    },
  },
  plugins: [],
};

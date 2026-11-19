const c = (name) => `rgb(var(--${name}) / <alpha-value>)`;
/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: c("bg"), surface: c("surface"), ink: c("ink"), muted: c("muted"), line: c("line"),
        accent: c("accent"), "on-accent": c("on-accent"), signal: c("signal"), ok: c("ok"), bad: c("bad"),
      },
      fontFamily: {
        sans: ['"Schibsted Grotesk"', "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};

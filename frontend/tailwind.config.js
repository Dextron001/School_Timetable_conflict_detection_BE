/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      // These read from CSS variables defined in index.css so you can
      // re-theme the whole app by editing a few variables.
      colors: {
        brand: {
          DEFAULT: "rgb(var(--brand) / <alpha-value>)",
          soft: "rgb(var(--brand-soft) / <alpha-value>)",
        },
        ink: "rgb(var(--ink) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        surface: "rgb(var(--surface) / <alpha-value>)",
        card: "rgb(var(--card) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
      },
          fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        serif: ['Georgia', '"Times New Roman"', "Cambria", "serif"],
      },
      boxShadow: {
        soft: "0 10px 30px -12px rgb(0 0 0 / 0.25)",
      },
    },
  },
  plugins: [],
};

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        sand: "#f3ecdf",
        ink: "#1d1a17",
        ember: "#c85b34",
        moss: "#1f5f45",
        haze: "#fffaf2",
      },
      fontFamily: {
        sans: ['"Space Grotesk"', "sans-serif"],
        mono: ['"IBM Plex Mono"', "monospace"],
      },
      boxShadow: {
        panel: "0 24px 80px rgba(62, 43, 22, 0.16)",
      },
    },
  },
  plugins: [],
};

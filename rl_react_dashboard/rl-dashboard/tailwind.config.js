// REPLACE: tailwind.config.js

/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ['"DM Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "Menlo", "monospace"],
      },
    },
  },
  plugins: [
    // scrollbar-none utility for hiding scrollbars while keeping scroll behaviour
    function ({ addUtilities }) {
      addUtilities({
        ".scrollbar-none": {
          "-ms-overflow-style": "none",
          "scrollbar-width": "none",
          "&::-webkit-scrollbar": { display: "none" },
        },
        ".scrollbar-thin": {
          "scrollbar-width": "thin",
          "&::-webkit-scrollbar": { width: "4px", height: "4px" },
          "&::-webkit-scrollbar-track": { background: "transparent" },
          "&::-webkit-scrollbar-thumb": { background: "rgba(100,100,100,0.3)", "border-radius": "2px" },
        },
      });
    },
  ],
};

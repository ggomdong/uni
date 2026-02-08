/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./**/*.py",
  ],
  theme: {
    extend: {},
    screens: {
      // mobile-first
      sm: "640px",
      md: "768px",     // 모바일 기준(햄버거)
      lg: "1024px",    // 중간(상단네비)
      xl: "1280px",
      "2xl": "1536px",
      fhd: "1920px",   // ✅ 너희 기존 기준 (좌측 사이드바)
    },
  },
  plugins: [],
};
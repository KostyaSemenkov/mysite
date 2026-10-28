/** Сборка Tailwind для lemurqa.ru (замена CDN).
 *  Палитра ведёт в tokens.css через CSS-переменные → дуал-тема работает. */
module.exports = {
  content: ['./templates/**/*.html'],
  theme: {
    extend: {
      colors: {
        white: 'var(--title)',  // в светлой теме «белый» текст становится тёмным
        slate: { 950: 'var(--bg)', 900: 'var(--panel)', 800: 'var(--border)', 700: 'var(--border2)',
                 600: 'var(--accent-hov)', 500: 'var(--muted)', 400: 'var(--muted)', 300: 'var(--text)',
                 200: 'var(--text)', 100: 'var(--title)' },
        indigo: { 950: 'var(--accent-dim)', 900: 'var(--accent-dim)', 600: 'var(--accent)', 500: 'var(--accent-hov)',
                  400: 'var(--accent-light)', 300: 'var(--accent-lighter)' },
      },
      fontFamily: {
        sans: ['Manrope', 'Segoe UI', 'system-ui', 'sans-serif'],
        display: ['Unbounded', 'Manrope', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

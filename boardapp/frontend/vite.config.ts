import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Адреса для локальной разработки (на проде маршрутизацию делает Caddy):
//   VITE_API_ORIGIN    — бэкенд «Досок» (API и WebSocket)
//   VITE_STATIC_ORIGIN — сайт Django (tokens.css, иконки, theme.js)
// По умолчанию оба на :8000. Если Django запущен на другом порту, задайте
// VITE_STATIC_ORIGIN=http://localhost:<порт> — иначе стили темы не загрузятся.
const apiOrigin = process.env.VITE_API_ORIGIN ?? 'http://localhost:8000'
const staticOrigin = process.env.VITE_STATIC_ORIGIN ?? 'http://localhost:8000'

// https://vite.dev/config/
// Приложение живёт по пути /boards на основном сайте (Caddy срезает префикс)
export default defineConfig({
  plugins: [react()],
  base: '/boards/',
  server: {
    proxy: {
      '/boards/api': { target: apiOrigin, changeOrigin: true,
                       rewrite: (p) => p.replace(/^\/boards/, '') },
      '/static': { target: staticOrigin },
      '/boards/ws': { target: apiOrigin, ws: true,
                      rewrite: (p) => p.replace(/^\/boards/, '') },
    },
  },
})

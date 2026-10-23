import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
// Приложение живёт по пути /boards на основном сайте (Caddy срезает префикс)
export default defineConfig({
  plugins: [react()],
  base: '/boards/',
  server: {
    proxy: {
      '/boards/api': { target: 'http://localhost:8000', changeOrigin: true,
                       rewrite: (p) => p.replace(/^\/boards/, '') },
      '/static': { target: 'http://localhost:8000' },
      '/boards/ws': { target: 'http://localhost:8000', ws: true,
                      rewrite: (p) => p.replace(/^\/boards/, '') },
    },
  },
})

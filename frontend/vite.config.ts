import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies API + health calls to the FastAPI backend so the frontend
// code always talks to a relative `/api` base (works behind a reverse proxy too).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/healthz': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})

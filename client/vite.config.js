import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev server proxies /api calls to the Python backend so you avoid CORS issues
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8080,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})

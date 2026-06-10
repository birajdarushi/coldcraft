import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Support both standalone dev (localhost) and Docker (service name)
// Set VITE_API_PROXY_TARGET=http://api:8000 when running inside compose
const proxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true, // bind 0.0.0.0 so it is reachable from host when in Docker
    proxy: {
      // Proxy API and tracking to backend during `npm run dev`
      '/api': proxyTarget,
      '/track': proxyTarget,
      '/health': proxyTarget,
    },
  },
})

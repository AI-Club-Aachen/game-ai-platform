import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  define: {
    'import.meta.env.MAX_TURN_TIME_LIMIT_SECONDS': JSON.stringify(process.env.MAX_TURN_TIME_LIMIT_SECONDS),
  },
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    watch: {
      usePolling: true,
    },
  },
})

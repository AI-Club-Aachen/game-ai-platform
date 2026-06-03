import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const parseAllowedHosts = (allowOrigins?: string): string[] => {
  if (!allowOrigins) return []

  const normalized = allowOrigins.trim()
  let origins: string[] = []

  try {
    const parsed = JSON.parse(normalized)
    if (Array.isArray(parsed)) {
      origins = parsed
    }
  } catch {
    origins = normalized.split(',')
  }

  return origins
    .map((origin) => origin.trim().replace(/^['"]|['"]$/g, ''))
    .map((origin) => {
      try {
        return new URL(origin).hostname
      } catch {
        return origin.replace(/^https?:\/\//, '').split('/')[0].split(':')[0]
      }
    })
    .filter(Boolean)
}

const allowedHosts = parseAllowedHosts(process.env.ALLOW_ORIGINS)

// https://vitejs.dev/config/
export default defineConfig({
  define: {
    'import.meta.env.MAX_TURN_TIME_LIMIT_SECONDS': JSON.stringify(process.env.MAX_TURN_TIME_LIMIT_SECONDS),
  },
  plugins: [react()],
  server: {
    host: true,
    port: 3000,
    allowedHosts,
    watch: {
      usePolling: true,
    },
  },
})

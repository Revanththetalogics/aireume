import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/health': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      output: {
        manualChunks(id) {
          // React core (must come before generic vendor)
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/')) {
            return 'vendor-react'
          }
          // React Router
          if (id.includes('node_modules/react-router')) {
            return 'vendor-router'
          }
          // Recharts + d3 together to avoid circular refs
          if (id.includes('node_modules/recharts') || id.includes('node_modules/d3') || id.includes('node_modules/victory')) {
            return 'vendor-charts'
          }
          // html2pdf + jsPDF + canvas (large PDF generation lib)
          if (id.includes('node_modules/html2pdf') || id.includes('node_modules/jspdf') || id.includes('node_modules/html2canvas')) {
            return 'vendor-pdf'
          }
          // Framer Motion (animation)
          if (id.includes('node_modules/framer-motion')) {
            return 'vendor-motion'
          }
          // Admin pages into their own chunk
          if (id.includes('/src/pages/admin/') || id.includes('/src/pages/AdminDashboardPage')) {
            return 'chunk-admin'
          }
          // Other vendor libs
          if (id.includes('node_modules/')) {
            return 'vendor'
          }
        }
      }
    }
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/__tests__/setup.js'
  }
})

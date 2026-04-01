import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from "path"

export default defineConfig({
  plugins: [
    vue()
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'chat-rendering': ['markdown-it', 'highlight.js'],
          'naive-ui': ['naive-ui'],
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  }
})

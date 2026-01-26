import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src')
    }
  },
  server: {
    port: 5173,
    proxy: {
      // 学生端API
      '/api/student': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true
      },
      '/api/job': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true
      },
      '/api/common': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true
      },
      // 企业端API
      '/api/enterprise': {
        target: 'http://127.0.0.1:8002',
        changeOrigin: true
      },
      // 高校端API
      '/api/university': {
        target: 'http://127.0.0.1:8003',
        changeOrigin: true
      }
    }
  }
})

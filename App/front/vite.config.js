import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    watch: {
      usePolling: true, // 启用轮询
      interval: 100, // 轮询的时间间隔（毫秒）
    },
  },
})

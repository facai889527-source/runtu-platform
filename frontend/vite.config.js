import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // Authentication validates the public same-origin Host; do not replace it with the upstream address.
  server: { host: '127.0.0.1', proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false } } },
  preview: { host: '127.0.0.1', proxy: { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: false } } },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'node:path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  // Tauri: cố định cổng dev + im lặng cảnh báo HMR qua IPC
  clearScreen: false,
  server: { port: 5173, strictPort: true },
})

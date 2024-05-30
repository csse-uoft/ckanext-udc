import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  base: "/udc-react",
  plugins: [react()],
  optimizeDeps: {
    include: ['@mui/material/Tooltip', '@emotion/styled'],
  },
  build: {
    manifest: true,
    emptyOutDir: true,
    outDir: "../public/udc-react",
    // modulePreload: {
    //   polyfill: false
    // }
  },
})

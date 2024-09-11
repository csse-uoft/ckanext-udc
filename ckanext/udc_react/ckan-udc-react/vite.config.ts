import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fixReactVirtualized from 'esbuild-plugin-react-virtualized'

// https://vitejs.dev/config/
export default defineConfig({
  base: "/udc-react",
  plugins: [react()],
  optimizeDeps: {
    include: ['@emotion/styled'],
    esbuildOptions: {
      plugins: [fixReactVirtualized],
    },
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

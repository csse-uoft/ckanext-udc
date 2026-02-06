import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fixReactVirtualized from 'esbuild-plugin-react-virtualized'

// https://vitejs.dev/config/
const viteOrigin = process.env.VITE_ORIGIN
let hmrHost: string | undefined
let hmrPort: number | undefined

if (viteOrigin) {
  try {
    const url = new URL(viteOrigin)
    hmrHost = url.hostname
    hmrPort = url.port ? Number(url.port) : undefined
  } catch {
    hmrHost = undefined
    hmrPort = undefined
  }
}

export default defineConfig({
  base: "/udrc",
  plugins: [react()],
  server: {
    port: hmrPort ?? 5173,
    strictPort: true,
    hmr: {
      host: hmrHost ?? 'localhost',
      port: hmrPort ?? 5173,
      clientPort: hmrPort ?? 5173,
      path: "/udrc",
    },
  },
  optimizeDeps: {
    include: ['@emotion/styled'],
    esbuildOptions: {
      plugins: [fixReactVirtualized],
    },
  },
  build: {
    manifest: true,
    emptyOutDir: true,
    outDir: "../public/udrc",
    rollupOptions: {
      output: {
        manualChunks: {
          // mui: ['@mui/material'],
          // mui2: ['@mui/system', '@mui/icons-material', '@mui/base', '@emotion/react', '@emotion/styled'],
          // icons: ['@mui/icons-material'],
          react: ['react', 'react-dom', 'react-router-dom', 'react-router', 'react/jsx-runtime'],
          markdown: ['rehype-raw', 'react-markdown'],
          'codemirror-lang': ['@codemirror/lang-python', '@codemirror/lang-json'],
          // datagrid: ['@mui/x-data-grid'],
        }
      }
    }
    // modulePreload: {
    //   polyfill: false
    // }
  },
})

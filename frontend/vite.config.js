import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

export default defineConfig({
  plugins: [svelte()],
  base: './',
  resolve: {
    alias: {
      '@ecoal': path.resolve(__dirname, '../custom_components/ecoal/www')
    }
  },
  build: {
    outDir: path.resolve(__dirname, '../custom_components/ecoal/www'),
    emptyOutDir: false,
    rollupOptions: {
      output: {
        entryFileNames: 'bundle.js',
        chunkFileNames: 'chunks/[name].js',
        assetFileNames: (assetInfo) => {
          if (assetInfo.name && assetInfo.name.endsWith('.css')) {
            return 'bundle.css';
          }
          return 'assets/[name][extname]';
        },
      },
    },
  },
});

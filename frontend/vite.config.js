import path from 'path';
import { defineConfig } from 'vite';

export default defineConfig({
  base: '/dist/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        'cv-tools': path.resolve(__dirname, 'cv-tools.html'),
      },
    },
  },
});

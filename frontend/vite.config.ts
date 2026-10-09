import { defineConfig } from 'vite';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const rootDir = fileURLToPath(new URL('.', import.meta.url));
const apiProxy = {
  '/v1': 'http://localhost:8000',
  '/health': 'http://localhost:8000',
  '^/admin$': 'http://localhost:8000',
};
export default defineConfig({
  server: { proxy: apiProxy },
  preview: { proxy: apiProxy },
  build: { rollupOptions: { input: { app: resolve(rootDir, 'index.html'), admin: resolve(rootDir, 'admin.html') } } },
});

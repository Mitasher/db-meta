import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В dev-режиме /api уходит в nginx из docker-compose, он проксирует на бэкенд
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8090",
    },
  },
});

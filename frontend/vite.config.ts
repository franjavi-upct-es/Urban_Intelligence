// frontend/vite.config.ts
// Urban Intelligence Framework v2.0.0
// Vite build configuration

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";

// Use import.meta.url instead of __dirname — compatible with ESM and avoids
// the need for @types/node. `URL` is a global in modern Node / browser envs.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // Mirrors the paths in tsconfig.app.json so Vite and TS agree
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Proxy API requests to the FastAPI backend during development
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
      "/ws": {
        target: "ws://localhost:8000",
        ws: true,
        changeOrigin: true,
      },
      "/graphql": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    rollupOptions: {
      output: {
        // manualChunks must be a function in Rollup 4+ (Vite 5).
        // An object literal is no longer accepted.
        manualChunks(id: string) {
          if (id.includes("recharts")) return "charts";
          if (id.includes("@tanstack")) return "query";
          if (
            id.includes("react-dom") ||
            id.includes("react-router-dom") ||
            id.includes("node_modules/react/")
          ) {
            return "vendor";
          }
        },
      },
    },
  },
});

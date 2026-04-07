import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  base: "./",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:7860",
      "/envs": "http://localhost:7860",
    },
  },
  preview: {
    port: 4173,
  },
  test: {
    environment: "happy-dom",
    setupFiles: "./src/setupTests.ts",
    globals: true,
  },
});

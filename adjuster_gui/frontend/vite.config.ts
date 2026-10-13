import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://localhost:8010",
      "/health": "http://localhost:8010",
      "/claims.json": "http://localhost:8010",
      "/sample": "http://localhost:8010",
    },
  },
  build: {
    outDir: "dist",
  },
});

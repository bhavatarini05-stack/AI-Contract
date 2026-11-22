import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Backend URL for the dev proxy (override with API_TARGET=http://localhost:8010 npm run dev)
const target = process.env.API_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target, rewrite: (p) => p.replace(/^\/api/, "") } },
  },
});

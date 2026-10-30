import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// O proxy evita CORS em desenvolvimento: o navegador fala só com :5173.
const target = process.env.VITE_PROXY_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": target,
      "/ws": { target, ws: true },
    },
  },
});

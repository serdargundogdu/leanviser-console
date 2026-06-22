import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// /api istekleri backend'e (FastAPI :8000) proxy'lenir; ön ek KORUNUR.
// Backend de API'leri /api altında servis eder -> dev ile prod birebir aynı yol.
// Böylece tarayıcı tek origin görür, CORS gerekmez.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});

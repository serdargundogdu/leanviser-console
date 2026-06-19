import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// /api istekleri backend'e (FastAPI :8000) proxy'lenir; "/api" ön eki soyulur.
// Böylece tarayıcı tek origin görür, CORS gerekmez.
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});

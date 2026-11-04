import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development the browser talks only to Vite (localhost:5173).
// Vite forwards /api (HTTP) and /ws (WebSocket) to Django on port 8000,
// so cookies and CSRF work as a single origin.
const BACKEND = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  build: {
    // The editor chunk (Tiptap/ProseMirror + Yjs) is ~540 kB and is lazy-loaded
    // only on the document page, so a slightly higher limit is expected.
    chunkSizeWarningLimit: 600,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: false },
      "/ws": { target: BACKEND, ws: true, changeOrigin: false },
    },
  },
});

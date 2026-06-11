import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 6132,
    proxy: {
      "/api": "http://localhost:5174"
    }
  },
  preview: {
    port: 6132
  }
});

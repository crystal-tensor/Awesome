import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { app as apiApp } from "./server.js";

const __dirname = fileURLToPath(new URL(".", import.meta.url));

const expressPlugin = {
  name: 'express-plugin',
  configureServer(server) {
    server.middlewares.use(apiApp);
  },
  configurePreviewServer(server) {
    server.middlewares.use(apiApp);
  }
};

export default defineConfig({
  plugins: [react(), expressPlugin],
  build: {
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        domesticModel: resolve(__dirname, "index1.html"),
        globalModel: resolve(__dirname, "index2.html"),
        strategy: resolve(__dirname, "strategy.html"),
        model: resolve(__dirname, "model.html"),
        modelApi: resolve(__dirname, "model-api/index.html"),
        globalMap: resolve(__dirname, "global_financial_map.html"),
        intelligenceLab: resolve(__dirname, "financial_intelligence_lab.html"),
        evolution: resolve(__dirname, "agent_finance_evolution.html")
      }
    }
  },
  server: {
    port: 6132,
    host: "0.0.0.0"
  },
  preview: {
    port: 6132,
    host: "0.0.0.0"
  }
});

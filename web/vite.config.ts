import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import type { UserConfig } from "vite";

type VitestUserConfig = UserConfig & {
  test: {
    environment: "jsdom";
    globals: true;
    setupFiles: string;
  };
};

const config: VitestUserConfig = {
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: false,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
};

export default defineConfig(config);

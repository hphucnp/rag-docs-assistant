import { fileURLToPath, URL } from "node:url";

import { defineConfig, loadEnv } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const proxyTarget = env.VITE_DEV_PROXY_TARGET || "http://localhost:8000";
  const allowedHosts = (env.VITE_ALLOWED_HOSTS || "beestack.vn")
    .split(",")
    .map((host) => host.trim())
    .filter(Boolean);

  return {
    plugins: [vue()],
    base: command === "build" ? "/" : "/",
    build: {
      outDir: fileURLToPath(new URL("../app/static/demo_app", import.meta.url)),
      emptyOutDir: true,
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      allowedHosts,
      proxy: {
        "/api": {
          target: proxyTarget,
          changeOrigin: true,
        },
        "/health": {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  };
});

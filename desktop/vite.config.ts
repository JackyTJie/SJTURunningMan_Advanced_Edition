import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Tauri 在开发时从固定端口加载前端；发布时把同样的构建产物嵌入可执行文件。
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    watch: { ignored: ["**/src-tauri/**"] },
  },
  build: {
    target: "chrome105",
    sourcemap: false,
  },
});

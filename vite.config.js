import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const repo = process.env.GITHUB_REPOSITORY?.split("/")[1] ?? "bleague-viewer";
const isCI = Boolean(process.env.GITHUB_ACTIONS);

export default defineConfig({
  plugins: [react()],
  base: process.env.VITE_BASE ?? (isCI ? `/${repo}/` : "/"),
  server: {
    fs: { allow: [".."] },
  },
});

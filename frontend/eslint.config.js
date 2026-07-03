import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import tseslint from "typescript-eslint";

export default tseslint.config(
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    // .js 파일은 tsconfig의 DOM lib 타입 인식 대상이 아니므로
    // fetch/window 등 브라우저 전역을 명시적으로 등록해야 no-undef 오탐이 없음
    files: ["**/*.js"],
    languageOptions: {
      globals: globals.browser,
    },
  },
  {
    plugins: {
      "react-hooks": reactHooks,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // TSC already enforces types; avoid duplicate errors in CI
      "@typescript-eslint/no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      "@typescript-eslint/no-explicit-any": "warn",
    },
  },
  {
    // Ignore build output and config files
    ignores: ["dist/**", "node_modules/**", "vite.config.*", "vitest.config.*"],
  }
);

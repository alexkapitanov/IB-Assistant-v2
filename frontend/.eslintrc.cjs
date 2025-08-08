/* eslint-env node */
module.exports = {
  root: true,
  env: { browser: true, es2023: true, node: true },
  parser: "@typescript-eslint/parser",
  parserOptions: { ecmaVersion: "latest", sourceType: "module" },
  plugins: ["@typescript-eslint", "react"],
  extends: [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended",
    "plugin:react/recommended",
    "plugin:react/jsx-runtime",
    "prettier"
  ],
  settings: { react: { version: "detect" } },
  ignorePatterns: ["dist", "node_modules"],
  rules: {
    "react/prop-types": "off"
  }
};

module.exports = {
  env: {
    browser: true,
    es2021: true,
  },
  extends: ["eslint:recommended", "plugin:react-hooks/recommended"],
  parser: "@typescript-eslint/parser",
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  plugins: ["@typescript-eslint", "react-refresh"],
  globals: {
    vi: "readonly",
    describe: "readonly",
    it: "readonly",
    expect: "readonly",
  },
  rules: {
    "react-refresh/only-export-components": "warn",
  },
};

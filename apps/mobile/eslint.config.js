// https://docs.expo.dev/guides/using-eslint/
const { defineConfig } = require("eslint/config");
const expoConfig = require("eslint-config-expo/flat");

module.exports = defineConfig([
  expoConfig,
  { ignores: ["dist/*"] },
  // React Three Fiber elements take three.js props (object, args, intensity…) that this rule doesn't know.
  { rules: { "react/no-unknown-property": "off" } },
]);

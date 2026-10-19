// Metro config: lets the app import shared packages from ../../packages and load .glb avatars.
const { getDefaultConfig } = require("expo/metro-config");
const path = require("path");

const projectRoot = __dirname;
const monorepoRoot = path.resolve(projectRoot, "../..");

const config = getDefaultConfig(projectRoot);

config.watchFolders = [path.resolve(monorepoRoot, "packages")];
config.resolver.nodeModulesPaths = [path.resolve(projectRoot, "node_modules")];
config.resolver.unstable_enableSymlinks = true;
config.resolver.assetExts.push("glb", "gltf");

module.exports = config;

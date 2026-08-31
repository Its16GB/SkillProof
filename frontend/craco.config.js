const path = require("path");

function makeDevServerV5Compatible(devServerConfig) {
  const {
    https,
    onAfterSetupMiddleware,
    onBeforeSetupMiddleware,
    setupMiddlewares,
    ...compatibleConfig
  } = devServerConfig;

  compatibleConfig.server =
    typeof https === "object"
      ? { type: "https", options: https }
      : https
        ? "https"
        : "http";

  compatibleConfig.setupMiddlewares = (middlewares, devServer) => {
    if (onBeforeSetupMiddleware) onBeforeSetupMiddleware(devServer);
    if (setupMiddlewares) middlewares = setupMiddlewares(middlewares, devServer);
    if (onAfterSetupMiddleware) onAfterSetupMiddleware(devServer);
    return middlewares;
  };
  return compatibleConfig;
}

const config = {
  eslint: {
    configure: {
      extends: ["plugin:react-hooks/recommended"],
      rules: {
        "react-hooks/rules-of-hooks": "error",
        "react-hooks/exhaustive-deps": "warn",
      },
    },
  },
  webpack: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
};

config.devServer = (devServerConfig) => makeDevServerV5Compatible(devServerConfig);
module.exports = config;

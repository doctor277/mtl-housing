import type { NextConfig } from "next";
import { PREVIEW_BOTS } from "./lib/bots";

const nextConfig: NextConfig = {
  cacheComponents: true,
  // Link previews in WhatsApp, Messenger, iMessage, Discord and Telegram (see lib/bots.ts).
  htmlLimitedBots: PREVIEW_BOTS,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;

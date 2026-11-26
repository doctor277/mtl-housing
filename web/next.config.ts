import type { NextConfig } from "next";
import { PREVIEW_BOTS } from "./lib/bots";

const nextConfig: NextConfig = {
  cacheComponents: true,
  // Link previews in WhatsApp, Messenger, iMessage, Discord and Telegram (see lib/bots.ts).
  htmlLimitedBots: PREVIEW_BOTS,
  partialPrefetching: true,
  experimental: {
    // Two root layouts (French, English; M5.3b) leave no single layout for a 404, so the
    // bilingual app/global-not-found.tsx stands alone (Next.js docs, not-found).
    globalNotFound: true,
  },
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

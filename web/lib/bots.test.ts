import { describe, expect, it } from "vitest";
import { PREVIEW_BOTS } from "./bots";

// The link-preview user agents of the apps the owner's users share on (M5.1), as their
// publishers document them (sources in the M5.1 PR).
const PREVIEW_FETCHERS: Record<string, string> = {
  WhatsApp: "WhatsApp/2.23.20.0 A",
  Messenger: "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
  iMessage:
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.4 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.4 facebookexternalhit/1.1 Facebot Twitterbot/1.0",
  Discord: "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
  Telegram: "TelegramBot (like TwitterBot)",
};

describe("link-preview bots", () => {
  it.each(Object.entries(PREVIEW_FETCHERS))("%s gets the metadata in <head>", (_, ua) => {
    expect(PREVIEW_BOTS.test(ua)).toBe(true);
  });

  it("matches Telegram by its own name, not only through 'like TwitterBot'", () => {
    expect(PREVIEW_BOTS.test("TelegramBot")).toBe(true);
  });

  it("leaves people's browsers on streamed metadata", () => {
    expect(
      PREVIEW_BOTS.test(
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1",
      ),
    ).toBe(false);
  });
});

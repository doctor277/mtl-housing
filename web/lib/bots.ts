// Link-preview bots that get the page's metadata in <head> before the body (blocking metadata)
// instead of streamed later in the body, which a fetcher that doesn't run JavaScript can miss.
// Used by next.config.ts (htmlLimitedBots). Built from Next's own default list, so its updates
// still apply, plus "TelegramBot": Telegram's fetcher ("TelegramBot (like TwitterBot)") matches
// the default only through "like TwitterBot" (owner, M5.1: WhatsApp, Messenger, iMessage, Discord
// and Telegram must all get previews).
//
// Trade-off: these bots wait for the page's metadata before any HTML is sent. People's browsers
// are not affected.
import { HTML_LIMITED_BOT_UA_RE } from "next/dist/shared/lib/router/utils/html-bots";

export const PREVIEW_BOTS = new RegExp(`${HTML_LIMITED_BOT_UA_RE.source}|TelegramBot`, "i");

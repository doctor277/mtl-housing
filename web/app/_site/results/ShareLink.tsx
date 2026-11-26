"use client";

// Shareable link (M5.1, owner's M5 decision 4): a "Copy link" button that copies the clean link
// of this search (no empty budget, no open card; view and sort kept), and the same clean link in
// the address bar, so copying from the browser shares it too. The button needs JavaScript, so it
// only appears once the page runs it.
import { useEffect, useState, useSyncExternalStore } from "react";
import type { Lang } from "@/lib/localized";
import { getStrings } from "@/lib/strings";

const noSubscription = () => () => {};

export default function ShareLink({ path, lang }: { path: string; lang: Lang }) {
  const t = getStrings(lang).results;
  // False while rendering on the server (and without JavaScript), true once the page runs.
  const ready = useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );
  const [status, setStatus] = useState<"idle" | "copied" | "failed">("idle");

  useEffect(() => {
    // Tidy the address bar: same page, clean query (drops "budget=" and "open=…").
    if (`${window.location.pathname}${window.location.search}` !== path) {
      window.history.replaceState(null, "", path);
    }
  }, [path]);

  useEffect(() => {
    if (status !== "copied") return;
    const timer = setTimeout(() => setStatus("idle"), 2500);
    return () => clearTimeout(timer);
  }, [status]);

  if (!ready) return null;

  const copy = async () => {
    // Clear first, so a second press changes the live region again and is announced again.
    setStatus("idle");
    try {
      await navigator.clipboard.writeText(`${window.location.origin}${path}`);
      setStatus("copied");
    } catch {
      setStatus("failed");
    }
  };

  return (
    <span className="inline-flex flex-wrap items-center gap-x-3">
      <button
        type="button"
        onClick={copy}
        className="inline-flex min-h-11 cursor-pointer items-center font-semibold text-link underline"
      >
        {t.copyLink}
      </button>
      <span role="status" className="text-sm text-ink-muted">
        {status === "copied" ? t.linkCopied : status === "failed" ? t.copyFailed : ""}
      </span>
    </span>
  );
}

"use client";

// After "Show details" on the map: the results stream in after the page loads, so the
// browser's own #hood-<id> jump finds nothing. Once the card is there, scroll to it and move
// keyboard focus to its summary.
import { useEffect } from "react";

export default function ScrollToCard({ id }: { id: string }) {
  useEffect(() => {
    const card = document.getElementById(`hood-${id}`);
    if (!card) return;
    card.scrollIntoView({ block: "start" });
    card.querySelector("summary")?.focus({ preventScroll: true });
  }, [id]);
  return null;
}

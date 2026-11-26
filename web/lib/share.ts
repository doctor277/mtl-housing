// Sharing a search (M5.1, owner's M5 decision 4): the summary line shown on the results page
// and the link preview's title and description, built from the parsed search, in the page's
// language (M5.3b). Wording in lib/strings; the clean link itself is lib/search.ts searchQuery.

import type { Search } from "./search";
import type { Strings } from "./strings";

/** "UdeM · 3½ · up to $1,500 a month · 45 min max". */
export function summaryLine(s: Search, campusLabel: string, t: Strings): string {
  return [
    campusLabel,
    t.form.size.labels[s.size],
    s.budget === null ? t.results.noBudget : t.results.budget(t.format.dollars(s.budget)),
    t.results.maxCommute(s.maxCommute),
  ].join(" · ");
}

/** Link preview of a search: text only (no image). */
export function sharePreview(
  s: Search,
  campusLabel: string,
  t: Strings,
): { title: string; description: string } {
  const budget = s.budget === null ? null : t.format.dollars(s.budget);
  return {
    title: t.share.title(campusLabel, t.form.size.labels[s.size], budget, s.maxCommute),
    description: t.share.description(campusLabel, t.share.sizeInSentence[s.size], s.maxCommute, budget),
  };
}

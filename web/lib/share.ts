// Sharing a search (M5.1, owner's M5 decision 4): the summary line shown on the results page
// and the link preview's title and description, built from the parsed search. Wording in
// lib/strings; the clean link itself is lib/search.ts searchQuery.

import type { Search } from "./search";
import { strings } from "./strings";

const t = strings.results;

/** "UdeM · 3½ · up to $1,500 a month · 45 min max". */
export function summaryLine(s: Search, campusLabel: string): string {
  return [
    campusLabel,
    strings.form.size.labels[s.size],
    s.budget === null ? t.noBudget : t.budget(strings.format.dollars(s.budget)),
    t.maxCommute(s.maxCommute),
  ].join(" · ");
}

/** Link preview of a search: text only (no image). */
export function sharePreview(s: Search, campusLabel: string): { title: string; description: string } {
  const budget = s.budget === null ? null : strings.format.dollars(s.budget);
  return {
    title: strings.share.title(campusLabel, strings.form.size.labels[s.size], budget, s.maxCommute, strings.siteName),
    description: strings.share.description(campusLabel, strings.share.sizeInSentence[s.size], s.maxCommute, budget),
  };
}

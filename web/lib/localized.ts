// Text the data files carry in both languages (M5.3a, owner's M5 decision 5): campus and
// building names, credits, CMHC's grade words, crosswalk notes, out-of-scope reasons. The
// pipeline writes them as {"en": ..., "fr": ...}; numbers never depend on the language.

export type Lang = "en" | "fr";

export type Localized = Record<Lang, string>;

/** The text in one language. */
export function inLang(text: Localized, lang: Lang): string {
  return text[lang];
}

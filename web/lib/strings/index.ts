// The site's strings in each language (M5.3b): French is the default at /, English at /en
// (owner's M5 decision 7). Every page and component picks its language's strings with
// getStrings(lang); there is no global language.
import type { Lang } from "../localized";
import { en, type Strings } from "./en";
import { fr } from "./fr";

export type { Strings } from "./en";
export { en, fr };

const BY_LANG: Record<Lang, Strings> = { en, fr };

export function getStrings(lang: Lang): Strings {
  return BY_LANG[lang];
}

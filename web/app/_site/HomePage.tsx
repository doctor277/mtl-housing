// First screen (M4): one line saying what the site does, then the search. No sign-up. In each
// language (M5.3b): French at /, English at /en.
import Link from "next/link";
import { campusOptions, departureWindow } from "@/lib/commute";
import { loadCommute } from "@/lib/data";
import type { Lang } from "@/lib/localized";
import { PATHS } from "@/lib/routes";
import { EXAMPLE_SEARCH, searchQuery } from "@/lib/search";
import { getStrings } from "@/lib/strings";
import SearchForm from "./SearchForm";

export default async function HomePage({ lang }: { lang: Lang }) {
  const s = getStrings(lang);
  const commute = await loadCommute();
  const campuses = campusOptions(commute, s);
  // The example link appears only if its campus is in the data (and it has a budget).
  const exampleCampus = campuses.find((c) => c.key === EXAMPLE_SEARCH.campus);
  const exampleLabel =
    exampleCampus &&
    EXAMPLE_SEARCH.budget !== null &&
    s.example.label(
      exampleCampus.label,
      s.form.size.labels[EXAMPLE_SEARCH.size],
      EXAMPLE_SEARCH.budget,
      EXAMPLE_SEARCH.maxCommute,
    );
  return (
    <>
      <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tight text-balance sm:text-4xl">
        {s.home.title}
      </h1>
      <p className="mt-3 max-w-prose text-ink-muted">{s.home.intro(Object.keys(commute.results).length)}</p>
      {exampleLabel && (
        <p className="mt-2 flex flex-wrap items-center gap-x-2">
          <span className="text-ink-muted">{s.example.lead}</span>
          <Link
            href={`${PATHS[lang].results}?${searchQuery(EXAMPLE_SEARCH)}`}
            className="inline-flex min-h-11 items-center font-semibold text-link underline"
          >
            {exampleLabel}
          </Link>
        </p>
      )}
      <SearchForm
        lang={lang}
        campuses={campuses.map((c) => ({ value: c.key, label: c.label }))}
        departure={departureWindow(commute.meta, s)}
      />
    </>
  );
}

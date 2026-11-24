// First screen (M4): one line saying what the site does, then the search. No sign-up.
import { campusOptions, departureWindow } from "@/lib/commute";
import Link from "next/link";
import { loadCommute } from "@/lib/data";
import { EXAMPLE_SEARCH, searchQuery } from "@/lib/search";
import { strings } from "@/lib/strings";
import SearchForm from "./SearchForm";

export default async function Home() {
  const commute = await loadCommute();
  // The example link appears only if its campus is in the data.
  const exampleCampus = campusOptions(commute).find((c) => c.key === EXAMPLE_SEARCH.campus);
  const exampleLabel = exampleCampus && [
    exampleCampus.label,
    strings.form.size.labels[EXAMPLE_SEARCH.size],
    `$${strings.format.dollars(EXAMPLE_SEARCH.budget ?? 0)}`,
    strings.form.maxCommute.option(EXAMPLE_SEARCH.maxCommute),
  ].join(", ");
  return (
    <>
      <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tight text-balance sm:text-4xl">
        {strings.home.title}
      </h1>
      <p className="mt-3 max-w-prose text-ink-muted">
        {strings.home.intro(Object.keys(commute.results).length)}
      </p>
      {exampleLabel && (
        <p className="mt-2 flex flex-wrap items-center gap-x-2">
          <span className="text-ink-muted">{strings.example.lead}</span>
          <Link
            href={`/results?${searchQuery(EXAMPLE_SEARCH)}`}
            className="inline-flex min-h-11 items-center font-semibold text-link underline"
          >
            {exampleLabel}
          </Link>
        </p>
      )}
      <SearchForm
        campuses={campusOptions(commute).map((c) => ({ value: c.key, label: c.label }))}
        departure={departureWindow(commute.meta)}
      />
    </>
  );
}

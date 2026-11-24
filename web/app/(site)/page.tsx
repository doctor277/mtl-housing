// First screen (M4): one line saying what the site does, then the search. No sign-up.
import { campusOptions, departureWindow } from "@/lib/commute";
import { loadCommute } from "@/lib/data";
import { strings } from "@/lib/strings";
import SearchForm from "./SearchForm";

export default async function Home() {
  const commute = await loadCommute();
  return (
    <>
      <h1 className="text-[1.75rem] leading-tight font-semibold tracking-tight text-balance sm:text-4xl">
        {strings.home.title}
      </h1>
      <p className="mt-3 max-w-prose text-ink-muted">
        {strings.home.intro(Object.keys(commute.results).length)}
      </p>
      <SearchForm
        campuses={campusOptions(commute).map((c) => ({ value: c.key, label: c.label }))}
        departure={departureWindow(commute.meta)}
      />
    </>
  );
}

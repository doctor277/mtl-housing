// Results. PLACEHOLDER until M4.2 builds the shortlist: it checks the search, repeats it, says
// plainly that the shortlist isn't built yet and points to the map. It shows no results.
import type { Metadata } from "next";
import Link from "next/link";
import { Suspense } from "react";
import { campusOptions } from "@/lib/commute";
import { loadCommute } from "@/lib/data";
import { formatDollars } from "@/lib/rent";
import { BUDGET_STEP, MAX_COMMUTE_MIN, parseSearch, type SearchField } from "@/lib/search";
import { strings } from "@/lib/strings";

const t = strings.results;

export const metadata: Metadata = { title: `${t.title} · ${strings.siteName}` };

const linkClass = "font-semibold text-link underline";

function invalidMessage(field: SearchField): string {
  if (field === "budget") return t.invalid.budget(BUDGET_STEP);
  if (field === "maxCommute") return t.invalid.maxCommute(MAX_COMMUTE_MIN);
  return t.invalid[field];
}

// searchParams is request data: it renders inside Suspense (Cache Components).
export default function Results({ searchParams }: PageProps<"/results">) {
  return (
    <Suspense fallback={<p className="text-ink-muted">{t.loading}</p>}>
      <SearchSummary searchParams={searchParams} />
    </Suspense>
  );
}

async function SearchSummary({ searchParams }: Pick<PageProps<"/results">, "searchParams">) {
  const commute = await loadCommute();
  const campuses = campusOptions(commute);
  const parsed = parseSearch(
    await searchParams,
    campuses.map((c) => c.key),
  );

  if (!parsed.ok) {
    return (
      <>
        <h1 className="text-2xl leading-tight font-semibold tracking-tight">{t.invalidTitle}</h1>
        <ul className="mt-4 list-disc pl-5 text-error">
          {parsed.errors.map((e) => (
            <li key={e}>{invalidMessage(e)}</li>
          ))}
        </ul>
        <p className="mt-6">
          <Link href="/" className={linkClass}>
            {t.changeSearch}
          </Link>
        </p>
      </>
    );
  }

  const s = parsed.search;
  const summary = [
    campuses.find((c) => c.key === s.campus)!.label,
    strings.form.size.labels[s.size],
    s.budget === null ? t.noBudget : t.budget(formatDollars(s.budget)),
    t.maxCommute(s.maxCommute),
  ];

  return (
    <>
      <h1 className="text-2xl leading-tight font-semibold tracking-tight">{t.title}</h1>
      <p className="mt-3 text-ink-muted">{summary.join(" · ")}</p>
      <p className="mt-2">
        <Link href="/" className={linkClass}>
          {t.changeSearch}
        </Link>
      </p>
      <div className="mt-8 max-w-prose border-t border-line pt-6">
        <p>{t.notBuilt}</p>
        <p className="mt-2">{t.mapNote}</p>
        <p className="mt-4">
          <Link href="/map" className={linkClass}>
            {t.openMap}
          </Link>
        </p>
      </div>
    </>
  );
}

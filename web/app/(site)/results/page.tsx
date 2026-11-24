// Results (M4.2): the shortlist. Rules in lib/shortlist.ts (owner's M4 decisions). Cards
// first; the map becomes a second view in M4.3. Works without JavaScript: the order toggle
// is two links, "show more" and the detail panels are native <details>.
import type { Metadata } from "next";
import Link from "next/link";
import { type ReactNode, Suspense } from "react";
import { campusOptions, departureWindow } from "@/lib/commute";
import { loadCommute, loadHoods, loadRent } from "@/lib/data";
import { formatDollars, formatRent } from "@/lib/rent";
import {
  MAX_COMMUTE_MIN,
  parseSearch,
  parseSort,
  type Search,
  type SearchField,
  searchQuery,
} from "@/lib/search";
import { buildShortlist, type GroupKey, SLIGHTLY_OVER_PCT, type ShortlistItem, type SortKey } from "@/lib/shortlist";
import { strings } from "@/lib/strings";
import SearchForm from "../SearchForm";
import HoodCard, { type CardContext } from "./HoodCard";

const t = strings.results;

export const metadata: Metadata = { title: `${t.title} · ${strings.siteName}` };

/** Cards shown per group before "Show N more". */
const FIRST = 5;

// Standalone links: a 44 px hit area, like every other control.
const linkClass = "inline-flex min-h-11 items-center font-semibold text-link underline";

function invalidMessage(field: SearchField): string {
  if (field === "maxCommute") return t.invalid.maxCommute(MAX_COMMUTE_MIN);
  return t.invalid[field];
}

// searchParams is request data: it renders inside Suspense (Cache Components).
export default function Results({ searchParams }: PageProps<"/results">) {
  return (
    <Suspense fallback={<p className="text-ink-muted">{t.loading}</p>}>
      <ResultsBody searchParams={searchParams} />
    </Suspense>
  );
}

function SortToggle({ search, sort }: { search: Search; sort: SortKey }) {
  const option = (key: SortKey, label: string) => (
    <Link
      href={`/results?${searchQuery(search, key)}`}
      aria-current={key === sort ? "true" : undefined}
      replace
      scroll={false}
      className={`flex min-h-11 items-center rounded-control border px-3 no-underline transition-colors duration-150 ease-out ${
        key === sort
          ? "border-ink bg-ink font-semibold text-white"
          : "border-control bg-surface hover:bg-hover active:bg-hover"
      }`}
    >
      {label}
    </Link>
  );
  return (
    <nav aria-label={t.sort.label} className="mt-6 flex flex-wrap items-center gap-2">
      <span className="mr-1 text-sm text-ink-muted">{t.sort.label}</span>
      {option("commute", t.sort.commute)}
      {option("rent", t.sort.rent)}
    </nav>
  );
}

function Group({
  heading,
  visualHeading,
  hint,
  items,
  card,
}: {
  heading: string;
  visualHeading: boolean;
  hint?: string;
  items: ShortlistItem[];
  card: (item: ShortlistItem) => ReactNode;
}) {
  const first = items.slice(0, FIRST);
  const rest = items.slice(FIRST);
  return (
    <section className="mt-8">
      <h2 className={visualHeading ? "text-lg font-semibold" : "sr-only"}>{heading}</h2>
      {hint && <p className="mt-1 text-sm text-ink-muted">{hint}</p>}
      {/* role="list": Safari drops the list role when list-style is none. */}
      <ol role="list" className="mt-3 flex flex-col gap-2">
        {first.map(card)}
      </ol>
      {rest.length > 0 && (
        <details className="group/more mt-2">
          {/* The control stays where it is (keyboard focus isn't lost); only its label changes. */}
          <summary className="flex min-h-11 cursor-pointer list-none items-center font-semibold text-link underline [&::-webkit-details-marker]:hidden">
            <span className="group-open/more:hidden">{t.showMore(rest.length)}</span>
            <span className="hidden group-open/more:inline">{t.showFewer}</span>
          </summary>
          <ol role="list" start={FIRST + 1} className="flex flex-col gap-2">
            {rest.map(card)}
          </ol>
        </details>
      )}
    </section>
  );
}

const HEADINGS: Record<GroupKey, string> = t.groups;
const HINTS: Partial<Record<GroupKey, string>> = {
  over: t.groupHint.over(SLIGHTLY_OVER_PCT),
  noData: t.groupHint.noData,
};

async function ResultsBody({ searchParams }: Pick<PageProps<"/results">, "searchParams">) {
  const [commute, rent, hoods, params] = await Promise.all([loadCommute(), loadRent(), loadHoods(), searchParams]);
  const campuses = campusOptions(commute);
  const parsed = parseSearch(
    params,
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
  const sort = parseSort(params);
  const list = buildShortlist(hoods, commute, rent, s, sort);
  const campusLabel = campuses.find((c) => c.key === s.campus)!.label;
  const sizeLabel = strings.form.size.labels[s.size];
  const summary = [
    campusLabel,
    sizeLabel,
    s.budget === null ? t.noBudget : t.budget(formatDollars(s.budget)),
    t.maxCommute(s.maxCommute),
  ];
  const ctx: CardContext = {
    campus: s.campus,
    campusMeta: commute.meta.campuses[s.campus],
    commuteMeta: commute.meta,
    rentMeta: rent.meta,
    campusLabel,
    sizeLabel,
    room: list.mode === "room",
  };
  const card = (item: ShortlistItem) => (
    <HoodCard
      key={item.id}
      item={item}
      commute={commute.results[item.id]![s.campus]!}
      rentEntry={s.size === "room" ? null : (rent.results[item.id]?.[s.size] ?? null)}
      ctx={ctx}
    />
  );
  // Cheapest first only with a budget and something to sort (decisions 1, 8).
  const sortable = list.mode === "budget" && list.groups.some((g) => g.key !== "noData");
  const longest = MAX_COMMUTE_MIN[MAX_COMMUTE_MIN.length - 1];

  return (
    <>
      <h1 className="text-2xl leading-tight font-semibold tracking-tight">{t.title}</h1>
      <p className="mt-2 text-ink-muted">{summary.join(" · ")}</p>

      <details className="mt-3">
        <summary className="flex min-h-11 cursor-pointer list-none items-center font-semibold text-link underline [&::-webkit-details-marker]:hidden">
          {t.changeSearch}
        </summary>
        <SearchForm
          campuses={campuses.map((c) => ({ value: c.key, label: c.label }))}
          departure={departureWindow(commute.meta)}
          initial={s}
          sort={sort}
          submitLabel={t.update}
          className="mt-4 mb-4 border-b border-line pb-8"
        />
      </details>

      {list.roomEstimate !== null && (
        <div className="mt-6 flex flex-col gap-1">
          <p className="font-semibold">{t.roomNote(formatRent(list.roomEstimate))}</p>
          {list.roomWarning && <p>{t.roomWarning(formatRent(list.roomEstimate))}</p>}
        </div>
      )}

      {sortable && <SortToggle search={s} sort={sort} />}

      {list.mode !== "room" && list.groups.some((g) => g.items.some((i) => i.rent !== null)) && (
        <p className="mt-6 text-sm text-ink-muted">{t.allEstimates}</p>
      )}

      {list.groups.map((g) => (
        <Group
          key={g.key}
          heading={HEADINGS[g.key]}
          visualHeading={g.key !== "all"}
          hint={g.key === "all" ? undefined : HINTS[g.key]}
          items={g.items}
          card={card}
        />
      ))}

      {list.groups.length === 0 && (
        <div className="mt-8">
          {list.withinCommute === 0 && list.tooFar === 0 ? (
            <p className="font-semibold">{t.noCommuteData(campusLabel)}</p>
          ) : list.withinCommute === 0 ? (
            <>
              <p className="font-semibold">{t.noneWithin(s.maxCommute, campusLabel)}</p>
              {s.maxCommute !== longest && <p className="mt-1">{t.tryLonger}</p>}
            </>
          ) : (
            <>
              <p className="font-semibold">{t.noneFits(list.withinCommute, s.maxCommute, SLIGHTLY_OVER_PCT)}</p>
              {list.cheapestHidden && (
                <p className="mt-1">
                  {t.cheapest(list.cheapestHidden.name, formatRent(list.cheapestHidden.rent))}
                </p>
              )}
              <p className="mt-1">{t.tryBudget(list.withinCommute)}</p>
            </>
          )}
        </div>
      )}

      {list.groups.length > 0 && list.hiddenOverBudget > 0 && (
        <p className="mt-6 text-sm text-ink-muted">{t.hiddenOverBudget(list.hiddenOverBudget, SLIGHTLY_OVER_PCT)}</p>
      )}

      {list.hiddenNoCommute > 0 && (
        <p className="mt-6 text-sm text-ink-muted">{t.hiddenNoCommute(list.hiddenNoCommute, campusLabel)}</p>
      )}

      <p className="mt-10 border-t border-line pt-6">
        <Link href="/map" className={linkClass}>
          {t.openMap}
        </Link>
      </p>
    </>
  );
}

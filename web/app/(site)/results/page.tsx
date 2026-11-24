// Results: the shortlist (M4.2) and its map view (M4.3). Rules in lib/shortlist.ts (owner's M4
// decisions). Cards first; the map is a second view the user switches to (decision 9). Works
// without JavaScript except the map itself: the view and sort toggles are links, "show more"
// and the detail panels are native <details>.
import type { Metadata } from "next";
import Link from "next/link";
import { type ReactNode, Suspense } from "react";
import { campusOptions, departureWindow } from "@/lib/commute";
import { loadCommute, loadHoods, loadRent } from "@/lib/data";
import {
  MAX_COMMUTE_MIN,
  parseOpen,
  parseSearch,
  parseSort,
  parseView,
  type ResultsView,
  type Search,
  type SearchField,
  searchQuery,
} from "@/lib/search";
import { buildShortlist, type GroupKey, SLIGHTLY_OVER_PCT, type ShortlistItem, type SortKey } from "@/lib/shortlist";
import { strings } from "@/lib/strings";
import SearchForm from "../SearchForm";
import HoodCard, { type CardContext } from "./HoodCard";
import ResultsMap, { type MapItem } from "./ResultsMap";
import ScrollToCard from "./ScrollToCard";

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

/** Two or more links drawn like the form's choices; the current one is ink. */
function LinkToggle({ label, options }: { label: string; options: { href: string; text: string; current: boolean }[] }) {
  return (
    <nav aria-label={label} className="flex flex-wrap items-center gap-2">
      <span className="mr-1 text-sm text-ink-muted">{label}</span>
      {options.map((o) => (
        <Link
          key={o.href}
          href={o.href}
          aria-current={o.current ? "true" : undefined}
          replace
          scroll={false}
          className={`flex min-h-11 items-center rounded-control border px-3 no-underline transition-colors duration-150 ease-out ${
            o.current ? "border-ink bg-ink font-semibold text-white" : "border-control bg-surface hover:bg-hover active:bg-hover"
          }`}
        >
          {o.text}
        </Link>
      ))}
    </nav>
  );
}

function SortToggle({ search, sort }: { search: Search; sort: SortKey }) {
  return (
    <LinkToggle
      label={t.sort.label}
      options={(["commute", "rent"] as const).map((key) => ({
        href: `/results?${searchQuery(search, key)}`,
        text: t.sort[key],
        current: key === sort,
      }))}
    />
  );
}

function ViewToggle({ search, sort, view }: { search: Search; sort: SortKey; view: ResultsView }) {
  return (
    <LinkToggle
      label={t.view.label}
      options={(["list", "map"] as const).map((key) => ({
        href: `/results?${searchQuery(search, sort, key)}`,
        text: t.view[key],
        current: key === view,
      }))}
    />
  );
}

function Group({
  heading,
  visualHeading,
  hint,
  items,
  card,
  openId,
}: {
  heading: string;
  visualHeading: boolean;
  hint?: string;
  items: ShortlistItem[];
  card: (item: ShortlistItem) => ReactNode;
  openId: string | null;
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
        <details className="group/more mt-2" open={rest.some((i) => i.id === openId)}>
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
  const view = parseView(params);
  const openId = parseOpen(params);
  const list = buildShortlist(hoods, commute, rent, s, sort);
  const campusLabel = campuses.find((c) => c.key === s.campus)!.label;
  const sizeLabel = strings.form.size.labels[s.size];
  const summary = [
    campusLabel,
    sizeLabel,
    s.budget === null ? t.noBudget : t.budget(strings.format.dollars(s.budget)),
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
      open={item.id === openId}
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
          <p className="font-semibold">{t.roomNote(strings.format.rent(list.roomEstimate))}</p>
          {list.roomWarning && <p>{t.roomWarning(strings.format.rent(list.roomEstimate))}</p>}
        </div>
      )}

      <div className="mt-6 flex flex-col gap-3">
        <ViewToggle search={s} sort={sort} view={view} />
        {view === "list" && sortable && <SortToggle search={s} sort={sort} />}
      </div>

      {view === "list" && list.mode !== "room" && list.groups.some((g) => g.items.some((i) => i.rent !== null)) && (
        <p className="mt-6 text-sm text-ink-muted">{t.allEstimates}</p>
      )}

      {view === "list" &&
        list.groups.map((g) => (
          <Group
            key={g.key}
            heading={HEADINGS[g.key]}
            visualHeading={g.key !== "all"}
            hint={g.key === "all" ? undefined : HINTS[g.key]}
            items={g.items}
            card={card}
            openId={openId}
          />
        ))}

      {view === "list" && openId && list.groups.some((g) => g.items.some((i) => i.id === openId)) && (
        <ScrollToCard id={openId} />
      )}

      {view === "map" && (
        <ResultsMap
          campus={s.campus}
          campusLabel={campusLabel}
          size={s.size === "room" ? null : s.size}
          maxCommute={s.maxCommute}
          maxTripMin={commute.meta.max_trip_min}
          rentLevel={s.size === "room" ? null : rent.meta.montreal[s.size].statcan_asking}
          rentStep={rent.meta.rounding.step}
          items={list.groups.flatMap((g) =>
            g.items.map((i): MapItem => ({ id: i.id, group: g.key, minutes: i.minutes, rent: i.rent, label: i.label })),
          )}
          excluded={list.excluded}
          detailsBase={`/results?${searchQuery(s, sort)}`}
        />
      )}

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
                  {t.cheapest(list.cheapestHidden.name, strings.format.rent(list.cheapestHidden.rent))}
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

    </>
  );
}

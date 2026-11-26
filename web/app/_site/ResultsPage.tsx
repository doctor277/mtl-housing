// Results: the shortlist (M4.2) and its map view (M4.3), in each language (M5.3b: /resultats,
// /en/results). Rules in lib/shortlist.ts (owner's M4 decisions). Cards first; the map is a
// second view the user switches to (decision 9). The view and sort toggles are links, "show
// more" and the detail panels are native <details>. The map and "Copy link" need JavaScript.
// Note: the results stream in Suspense, so this page as a whole also needs JavaScript to show
// them (reported to the owner in M5.1).
import type { Metadata } from "next";
import Link from "next/link";
import { type ReactNode, Suspense } from "react";
import { campusOptions, departureWindow } from "@/lib/commute";
import { loadCommute, loadHoods, loadRent } from "@/lib/data";
import type { Lang } from "@/lib/localized";
import { PATHS } from "@/lib/routes";
import {
  MAX_COMMUTE_MIN,
  parseOpen,
  parseSearch,
  parseSort,
  parseView,
  type ResultsView,
  type SearchField,
  searchQuery,
} from "@/lib/search";
import { sharePreview, summaryLine } from "@/lib/share";
import { buildShortlist, type GroupKey, SLIGHTLY_OVER_PCT, type ShortlistItem, type SortKey } from "@/lib/shortlist";
import { getStrings, type Strings } from "@/lib/strings";
import { pageMetadata } from "./metadata";
import HoodCard, { type CardContext } from "./results/HoodCard";
import ResultsMap, { type MapItem } from "./results/ResultsMap";
import ScrollToCard from "./results/ScrollToCard";
import ShareLink from "./results/ShareLink";
import SearchForm from "./SearchForm";

type Params = Promise<Record<string, string | string[] | undefined>>;

/** Link previews (M5.1, decision 4): text only, the search's own title and description, in the
 * page's language, with the same search in the other language as its alternate. An invalid
 * search gets the page's plain title. */
export async function resultsMetadata(lang: Lang, searchParams: Params): Promise<Metadata> {
  const s = getStrings(lang);
  const [commute, params] = await Promise.all([loadCommute(), searchParams]);
  const campuses = campusOptions(commute, s);
  const parsed = parseSearch(
    params,
    campuses.map((c) => c.key),
  );
  if (!parsed.ok) return pageMetadata(lang, "results", `${s.results.title} · ${s.siteName}`);
  const search = parsed.search;
  const query = searchQuery(search, parseSort(params), parseView(params));
  const { title, description } = sharePreview(search, campuses.find((c) => c.key === search.campus)!.label, s);
  return {
    ...pageMetadata(lang, "results", title, query),
    description,
    openGraph: { title, description, type: "website", siteName: s.siteName, locale: s.meta.locale },
  };
}

/** Cards shown per group before "Show N more". */
const FIRST = 5;

// Standalone links: a 44 px hit area, like every other control.
const linkClass = "inline-flex min-h-11 items-center font-semibold text-link underline";

function invalidMessage(field: SearchField, s: Strings): string {
  if (field === "maxCommute") return s.results.invalid.maxCommute(MAX_COMMUTE_MIN);
  return s.results.invalid[field];
}

// searchParams is request data: it renders inside Suspense (Cache Components).
export default function ResultsPage({ lang, searchParams }: { lang: Lang; searchParams: Params }) {
  const t = getStrings(lang).results;
  return (
    <>
      {/* Outside the streamed part, so it shows when JavaScript is off (owner, M5.1). */}
      <noscript>
        <h1 className="text-2xl leading-tight font-semibold tracking-tight">{t.title}</h1>
        <p className="mt-4 font-semibold">{t.needsJavaScript}</p>
        {/* "Loading…" would never end without JavaScript. */}
        <style>{".results-loading{display:none}"}</style>
      </noscript>
      <Suspense fallback={<p className="results-loading text-ink-muted">{t.loading}</p>}>
        <ResultsBody lang={lang} searchParams={searchParams} />
      </Suspense>
    </>
  );
}

/** Two or more links drawn like the form's choices; the current one is ink. The label sits on
 * its own line above them, so longer French labels never push a choice onto a row of its own,
 * and the buttons of every toggle line up (Impeccable, M5.3b). */
function LinkToggle({ label, options }: { label: string; options: { href: string; text: string; current: boolean }[] }) {
  return (
    <nav aria-label={label}>
      <p className="text-sm text-ink-muted">{label}</p>
      <div className="mt-1 flex flex-wrap gap-2">
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
      </div>
    </nav>
  );
}

function Group({
  heading,
  visualHeading,
  hint,
  items,
  card,
  openId,
  s,
}: {
  heading: string;
  visualHeading: boolean;
  hint?: string;
  items: ShortlistItem[];
  card: (item: ShortlistItem) => ReactNode;
  openId: string | null;
  s: Strings;
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
            <span className="group-open/more:hidden">{s.results.showMore(rest.length)}</span>
            <span className="hidden group-open/more:inline">{s.results.showFewer}</span>
          </summary>
          <ol role="list" start={FIRST + 1} className="flex flex-col gap-2">
            {rest.map(card)}
          </ol>
        </details>
      )}
    </section>
  );
}

async function ResultsBody({ lang, searchParams }: { lang: Lang; searchParams: Params }) {
  const s = getStrings(lang);
  const t = s.results;
  const resultsPath = PATHS[lang].results;
  const [commute, rent, hoods, params] = await Promise.all([loadCommute(), loadRent(), loadHoods(), searchParams]);
  const campuses = campusOptions(commute, s);
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
            <li key={e}>{invalidMessage(e, s)}</li>
          ))}
        </ul>
        <p className="mt-6">
          <Link href={PATHS[lang].home} className={linkClass}>
            {t.changeSearch}
          </Link>
        </p>
      </>
    );
  }

  const search = parsed.search;
  const sort = parseSort(params);
  const view = parseView(params);
  const openId = parseOpen(params);
  const list = buildShortlist(hoods, commute, rent, search, sort);
  const campusLabel = campuses.find((c) => c.key === search.campus)!.label;
  const sizeLabel = s.form.size.labels[search.size];
  const ctx: CardContext = {
    s,
    campus: search.campus,
    campusMeta: commute.meta.campuses[search.campus],
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
      commute={commute.results[item.id]![search.campus]!}
      rentEntry={search.size === "room" ? null : (rent.results[item.id]?.[search.size] ?? null)}
      ctx={ctx}
      open={item.id === openId}
    />
  );
  // Cheapest first only with a budget and something to sort (decisions 1, 8).
  const sortable = list.mode === "budget" && list.groups.some((g) => g.key !== "noData");
  const longest = MAX_COMMUTE_MIN[MAX_COMMUTE_MIN.length - 1];
  const hasRents = list.mode !== "room" && list.groups.some((g) => g.items.some((i) => i.rent !== null));
  const headings: Record<GroupKey, string> = t.groups;
  const hints: Partial<Record<GroupKey, string>> = {
    over: t.groupHint.over(SLIGHTLY_OVER_PCT),
    noData: t.groupHint.noData,
  };
  const sortToggle = (
    <LinkToggle
      label={t.sort.label}
      options={(["commute", "rent"] as const).map((key: SortKey) => ({
        href: `${resultsPath}?${searchQuery(search, key)}`,
        text: t.sort[key],
        current: key === sort,
      }))}
    />
  );
  const viewToggle = (
    <LinkToggle
      label={t.view.label}
      options={(["list", "map"] as const).map((key: ResultsView) => ({
        href: `${resultsPath}?${searchQuery(search, sort, key)}`,
        text: t.view[key],
        current: key === view,
      }))}
    />
  );

  return (
    <>
      <h1 className="text-2xl leading-tight font-semibold tracking-tight">{t.title}</h1>
      <p className="mt-2 text-ink-muted">{summaryLine(search, campusLabel, s)}</p>

      {/* "Change search" and "Copy link" on one row, so the answer starts higher (design review
          DR5-1); the opened form takes the whole width and "Copy link" follows it. */}
      <div className="mt-2 flex flex-wrap items-start gap-x-6">
        <details className="open:w-full">
          <summary className="flex min-h-11 cursor-pointer list-none items-center font-semibold text-link underline [&::-webkit-details-marker]:hidden">
            {t.changeSearch}
          </summary>
          <SearchForm
            lang={lang}
            campuses={campuses.map((c) => ({ value: c.key, label: c.label }))}
            departure={departureWindow(commute.meta, s)}
            initial={search}
            sort={sort}
            submitLabel={t.update}
            className="mt-4 mb-4 border-b border-line pb-8"
          />
        </details>
        {/* The clean link of this search (no empty budget, no open card; view and sort kept). */}
        <ShareLink lang={lang} path={`${resultsPath}?${searchQuery(search, sort, view)}`} />
      </div>

      {list.roomEstimate !== null && (
        <div className="mt-4 flex flex-col gap-1">
          <p className="font-semibold">{t.roomNote(s.format.rent(list.roomEstimate))}</p>
          {list.roomWarning && <p>{t.roomWarning(s.format.rent(list.roomEstimate))}</p>}
        </div>
      )}

      {/* Stacked on phones; side by side from sm (DR5-1). Labels stay above (Impeccable). */}
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:gap-8">
        {viewToggle}
        {view === "list" && sortable && sortToggle}
      </div>

      {/* The map's popups don't badge plain estimates either (decision 16); in the map view this
          line sits under the legend instead (DR5-3). */}
      {view === "list" && hasRents && <p className="mt-4 text-sm text-ink-muted">{t.allEstimates}</p>}

      {view === "list" &&
        list.groups.map((g) => (
          <Group
            key={g.key}
            heading={headings[g.key]}
            visualHeading={g.key !== "all"}
            hint={g.key === "all" ? undefined : hints[g.key]}
            items={g.items}
            card={card}
            openId={openId}
            s={s}
          />
        ))}

      {view === "list" && openId && list.groups.some((g) => g.items.some((i) => i.id === openId)) && (
        <ScrollToCard id={openId} />
      )}

      {view === "map" && (
        <ResultsMap
          lang={lang}
          campus={search.campus}
          campusLabel={campusLabel}
          size={search.size === "room" ? null : search.size}
          maxCommute={search.maxCommute}
          maxTripMin={commute.meta.max_trip_min}
          rentLevel={search.size === "room" ? null : rent.meta.montreal[search.size].statcan_asking}
          rentStep={rent.meta.rounding.step}
          items={list.groups.flatMap((g) =>
            g.items.map((i): MapItem => ({ id: i.id, group: g.key, minutes: i.minutes, rent: i.rent, label: i.label })),
          )}
          excluded={list.excluded}
          detailsBase={`${resultsPath}?${searchQuery(search, sort)}`}
          rentDataLine={search.size === "room" ? null : s.rent.dataLine(rent.meta)}
          estimatesNote={hasRents ? t.allEstimates : null}
        />
      )}

      {list.groups.length === 0 && (
        <div className="mt-8">
          {list.withinCommute === 0 && list.tooFar === 0 ? (
            <p className="font-semibold">{t.noCommuteData(campusLabel)}</p>
          ) : list.withinCommute === 0 ? (
            <>
              <p className="font-semibold">{t.noneWithin(search.maxCommute, campusLabel)}</p>
              {search.maxCommute !== longest && <p className="mt-1">{t.tryLonger}</p>}
            </>
          ) : (
            <>
              <p className="font-semibold">{t.noneFits(list.withinCommute, search.maxCommute, SLIGHTLY_OVER_PCT)}</p>
              {list.cheapestHidden && (
                <p className="mt-1">{t.cheapest(list.cheapestHidden.name, s.format.rent(list.cheapestHidden.rent))}</p>
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

"use client";

// The results' map view (M4.3): the same neighbourhoods as the list, coloured by commute or
// rent; everything else is grey ("Not in your results") and its popup says why. The map is
// never the default view (M4 decision 9); the list stays one tap away. Wording: lib/strings.

import { useMemo, useState } from "react";
import { BIN_UPPER_MIN, COMMUTE_COLOURS, NO_RESIDENTS_COLOUR, NOT_IN_RESULTS_COLOUR } from "@/lib/legend";
import { BIN_PCT, binEdges, type LabelKey, RENT_COLOURS, RENT_FILL_OPACITY, RENT_NO_DATA_COLOUR, type ShownSize } from "@/lib/rent";
import type { Lang } from "@/lib/localized";
import { type ExcludedReason, type GroupKey, SLIGHTLY_OVER_PCT } from "@/lib/shortlist";
import { getStrings } from "@/lib/strings";
import QuartierMap, { CAMPUS_MARKER_COLOUR, escapeHtml, type Mode } from "../../QuartierMap";

export interface MapItem {
  id: string;
  group: GroupKey;
  minutes: number;
  rent: number | null;
  label: LabelKey | null;
}

const HATCH_CSS =
  "repeating-linear-gradient(135deg, #141414 0 2px, #ffffff 2px 3px, transparent 3px 8px), #f3f2ee";

function Swatch({
  colour,
  opacity = 1,
  background,
  outlined = false,
}: {
  colour?: string;
  opacity?: number;
  background?: string;
  /** The results' dark outline. */
  outlined?: boolean;
}) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block h-3 w-5 shrink-0 rounded-[2px] ring-inset ${outlined ? "ring-2 ring-ink" : "ring-1 ring-control/60"}`}
      style={{ background: background ?? colour, opacity }}
    />
  );
}

function LegendRow({ swatch, label, wide = false }: { swatch: React.ReactNode; label: string; wide?: boolean }) {
  return (
    <li className={`flex items-center gap-2 ${wide ? "col-span-full" : ""}`}>
      {swatch}
      <span>{label}</span>
    </li>
  );
}

export default function ResultsMap({
  lang,
  campus,
  campusLabel,
  size,
  maxCommute,
  maxTripMin,
  rentLevel,
  rentStep,
  items,
  excluded,
  detailsBase,
  rentDataLine,
}: {
  lang: Lang;
  campus: string;
  campusLabel: string;
  /** null for rooms: one citywide figure, so the map colours by commute only. */
  size: ShownSize | null;
  maxCommute: number;
  maxTripMin: number;
  /** Montréal asking rent and rounding step for `size` (rent legend). */
  rentLevel: number | null;
  rentStep: number;
  items: MapItem[];
  excluded: Record<string, ExcludedReason>;
  /** "/results?campus=…": the list view of this search; "&open=<id>" is added per card. */
  detailsBase: string;
  /** The rent data dates ("Data: CMHC (…) and Statistics Canada's experimental …"), rent mode. */
  rentDataLine: string | null;
}) {
  const strings = getStrings(lang);
  const t = strings.resultsMap;
  const [mode, setMode] = useState<Mode>("commute");
  const byId = useMemo(() => new Map(items.map((i) => [i.id, i])), [items]);

  const results = useMemo(
    () => ({
      ids: items.map((i) => i.id),
      popupHtml: (id: string) => {
        const item = byId.get(id);
        if (!item) {
          // A reason only when the shortlist recorded one; never a guessed claim.
          const why = excluded[id];
          const line =
            why === "tooFar"
              ? t.out.tooFar(maxCommute, campusLabel)
              : why === "overBudget"
                ? t.out.overBudget(SLIGHTLY_OVER_PCT)
                : why === "noCommute"
                  ? t.out.noCommute(campusLabel)
                  : t.out.unknown;
          return escapeHtml(line);
        }
        const lines: string[] = [];
        if (item.group !== "all") lines.push(escapeHtml(strings.results.groups[item.group]));
        lines.push(
          `<b>${escapeHtml(
            t.numbers(strings.card.minutes(item.minutes), item.rent === null ? null : strings.format.rent(item.rent)),
          )}</b>`,
        );
        if (item.label && item.label !== "neighbourhood") lines.push(escapeHtml(strings.rent.badges[item.label]));
        const href = `${detailsBase}&open=${encodeURIComponent(id)}#hood-${encodeURIComponent(id)}`;
        // The site's link treatment, with a 44 px hit area (the popup's only action).
        lines.push(
          `<a href="${escapeHtml(href)}" class="inline-flex min-h-11 items-center font-semibold text-link underline">${escapeHtml(t.showDetails)}</a>`,
        );
        return lines.join("<br>");
      },
    }),
    [items, byId, excluded, maxCommute, campusLabel, detailsBase, strings, t],
  );

  // Commute classes up to the search's max commute (every result is within it).
  const commuteLabels = strings.commute.classLabels(BIN_UPPER_MIN, maxTripMin);
  const shownClasses = BIN_UPPER_MIN.findIndex((u) => u >= maxCommute) + 1;
  const rentRanges = size && rentLevel ? strings.rent.classRanges(binEdges(rentLevel, rentStep), rentStep) : [];
  const rentPct = strings.rent.classPct(BIN_PCT);

  const modeButton = (key: Mode, label: string) => (
    <button
      type="button"
      aria-pressed={mode === key}
      onClick={() => setMode(key)}
      className={`min-h-11 cursor-pointer rounded-control border px-3 transition-colors duration-150 ease-out ${
        mode === key ? "border-ink bg-ink font-semibold text-white" : "border-control bg-surface hover:bg-hover active:bg-hover"
      }`}
    >
      {label}
    </button>
  );

  return (
    <section aria-label={strings.results.view.map} className="mt-6">
      {size && (
        <div role="group" aria-label={t.colourBy} className="mb-3 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-sm text-ink-muted">{t.colourBy}</span>
          {modeButton("commute", strings.map.modes.commute)}
          {modeButton("rent", strings.map.modes.rent)}
        </div>
      )}
      <div className="relative h-[60vh] min-h-80 overflow-hidden rounded-control border border-control bg-surface">
        {/* Under the map: visible until the basemap paints over it (design review DR-2). */}
        <p className="absolute inset-0 flex items-center justify-center text-sm text-ink-muted">
          {strings.map.loadingMap}
        </p>
        <QuartierMap lang={lang} mode={mode} size={size ?? "1br"} campus={campus} results={results} />
      </div>
      <p className="mt-3 text-sm text-ink-muted">{t.hint}</p>

      <div className="mt-4 text-sm">
        <p className="font-semibold">
          {mode === "commute" || !size ? t.commuteLegend(campusLabel) : t.rentLegend(strings.rent.sizeLabel(size))}
        </p>
        <ul
          className={`mt-2 grid gap-x-4 gap-y-1 ${mode === "rent" && size ? "grid-cols-1 sm:grid-cols-2" : "grid-cols-2 sm:grid-cols-3"}`}
        >
          {mode === "commute" || !size
            ? COMMUTE_COLOURS.slice(0, shownClasses).map((c, i) => (
                <LegendRow key={c} swatch={<Swatch colour={c} opacity={0.6} />} label={commuteLabels[i]} />
              ))
            : RENT_COLOURS.map((c, i) => (
                <LegendRow
                  key={c}
                  swatch={<Swatch colour={c} opacity={RENT_FILL_OPACITY} />}
                  label={strings.map.rentClass(rentPct[i], rentRanges[i])}
                />
              ))}
          {mode === "rent" && size && (
            <>
              <LegendRow swatch={<Swatch background={HATCH_CSS} />} label={strings.map.lowReliability} />
              <LegendRow swatch={<Swatch colour={RENT_NO_DATA_COLOUR} />} label={strings.map.notEnoughData} />
            </>
          )}
          <LegendRow swatch={<Swatch background="transparent" outlined />} label={t.inResults} />
          <LegendRow
            swatch={
              <span aria-hidden="true" className="flex w-5 shrink-0 justify-center">
                <span className="size-3 rounded-full" style={{ background: CAMPUS_MARKER_COLOUR }} />
              </span>
            }
            label={t.pin}
            wide
          />
          <LegendRow swatch={<Swatch colour={NOT_IN_RESULTS_COLOUR} />} label={t.notInResults} />
          <LegendRow
            swatch={
              <span
                aria-hidden="true"
                className="inline-block h-3 w-5 shrink-0 rounded-[2px] outline-[1.5px] -outline-offset-1 outline-ink outline-dashed"
                style={{ background: NO_RESIDENTS_COLOUR }}
              />
            }
            label={t.noResidents}
          />
        </ul>
        {mode === "rent" && size && rentDataLine && <p className="mt-3 text-xs text-ink-muted">{rentDataLine}</p>}
        <p className="mt-3 text-xs text-ink-muted">{strings.map.attribution(mode === "rent")}</p>
      </div>
    </section>
  );
}

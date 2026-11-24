// One shortlist card (name, commute, rent, reliability badge). Tapping it opens the detail
// panel in place: commute (median, range, buildings, flags, source) and rent (estimate,
// CMHC basis, source, data dates). A native <details>, so it needs no JavaScript.
import { type CampusMeta, type CampusResult, type CommuteFile, departureWindow, type TimeBlock } from "@/lib/commute";
import {
  BADGES,
  dataLine,
  detailLine,
  extraLines,
  formatRent,
  isLowReliability,
  type RentEntry,
  type RentMeta,
  roomLine,
  sourceLine,
} from "@/lib/rent";
import type { ShortlistItem } from "@/lib/shortlist";
import { strings } from "@/lib/strings";

const t = strings.detail;

export interface CardContext {
  campus: string;
  /** Short campus name, "UdeM". */
  campusLabel: string;
  campusMeta: CampusMeta;
  commuteMeta: CommuteFile["meta"];
  rentMeta: RentMeta;
  sizeLabel: string;
  room: boolean;
}

/** Whole minutes, or null when over the routing limit ("more than 2 hours"). */
function wholeMinutes(v: number | null): number | null {
  return v === null ? null : Math.round(v);
}

/** A building's median as shown: "27 min" or "more than 2 hours"; null = no data. */
function buildingTime(b: TimeBlock, maxMin: number): string | null {
  if (b.median !== null) return strings.card.minutes(Math.round(b.median));
  return b.over_max.includes("median") ? t.overMax(maxMin) : null;
}

function CommuteDetail({ r, ctx, minutes }: { r: CampusResult; ctx: CardContext; minutes: number }) {
  const max = ctx.commuteMeta.max_trip_min;
  const dests = ctx.campusMeta.destinations;
  const { start, end } = departureWindow(ctx.commuteMeta);
  const target = dests.length > 1 ? t.toClosestBuilding(ctx.campusLabel) : t.toPlace(dests[0].name);
  // p10 ≤ median ≤ the max commute, so p10 is always a number here.
  const lines: string[] = [t.median(minutes, target, start, end), t.range(Math.round(r.p10!), wholeMinutes(r.p90), max)];
  if (dests.length > 1) {
    const parts = dests.flatMap((d) => {
      const b = r.by_destination[d.id];
      const time = b ? buildingTime(b, max) : null;
      return time ? [{ name: d.name, time }] : [];
    });
    if (parts.length) lines.push(t.buildings(parts));
  }
  if (r.flags.includes("low_sample")) lines.push(t.lowSample(r.n_points));
  if (r.flags.includes("many_unreachable") && r.unreachable_share !== null) {
    lines.push(t.manyUnreachable(`${Math.round(r.unreachable_share * 100)}%`, max));
  }
  return (
    <section>
      <h3 className="font-semibold">{t.commuteHeading}</h3>
      {lines.map((l) => (
        <p key={l} className="mt-1">
          {l}
        </p>
      ))}
      <p className="mt-2 text-ink-muted">{t.commuteSource}</p>
    </section>
  );
}

function RentDetail({ e, ctx }: { e: RentEntry | null; ctx: CardContext }) {
  const heading = <h3 className="font-semibold">{t.rentHeading(ctx.sizeLabel)}</h3>;
  if (ctx.room) {
    return (
      <section>
        {heading}
        <p className="mt-1">{roomLine(ctx.rentMeta)}</p>
      </section>
    );
  }
  const entry: RentEntry = e ?? { estimate: null, label: "none", grade: null, coverage_pct: null, cmhc_areas: [] };
  return (
    <section>
      {heading}
      <p className="mt-1">
        {entry.estimate !== null && (
          <span className="font-semibold tabular-nums">{strings.card.perMonth(formatRent(entry.estimate))} · </span>
        )}
        {BADGES[entry.label]}
      </p>
      <p className="mt-1">{detailLine(entry, ctx.rentMeta)}</p>
      {extraLines(entry, ctx.rentMeta).map((l) => (
        <p key={l} className="mt-1">
          {l}
        </p>
      ))}
      {entry.estimate !== null && <p className="mt-2 text-ink-muted">{sourceLine()}</p>}
      <p className="mt-1 text-ink-muted">{dataLine(ctx.rentMeta)}</p>
    </section>
  );
}

/** Only real caveats get a badge on the card; "Estimate" is said once above the list
 * (owner, M4.2). An outline, never colour: solid for a wider area, dashed for weaker data. */
function Badge({ label }: { label: RentEntry["label"] }) {
  const dashed = isLowReliability(label) || label === "none";
  return (
    <span
      className={`inline-block rounded-full border border-control px-2 text-sm leading-6 text-ink ${
        dashed ? "border-dashed" : ""
      }`}
    >
      {BADGES[label]}
    </span>
  );
}

export default function HoodCard({
  item,
  commute,
  rentEntry,
  ctx,
}: {
  item: ShortlistItem;
  commute: CampusResult;
  rentEntry: RentEntry | null;
  ctx: CardContext;
}) {
  return (
    <li>
      <details className="group rounded-control border border-control bg-surface">
        {/* Grid: name | minutes | chevron, then borough | rent, then the badge on its own line,
            so a wide badge never squeezes the names. */}
        <summary className="grid min-h-12 cursor-pointer list-none grid-cols-[1fr_auto_auto] items-baseline gap-x-3 gap-y-1 rounded-control p-4 transition-colors duration-150 ease-out hover:bg-hover active:bg-hover [&::-webkit-details-marker]:hidden">
          <span className="min-w-0 leading-snug font-semibold">{item.name}</span>
          <span className="text-right font-semibold tabular-nums">{strings.card.minutes(item.minutes)}</span>
          <svg
            aria-hidden="true"
            viewBox="0 0 20 20"
            className="row-span-3 size-5 self-start text-ink-muted transition-transform duration-150 ease-out group-open:rotate-180"
          >
            <path d="M5 7.5 10 12.5 15 7.5" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span className="min-w-0 text-sm text-ink-muted">{item.borough !== item.name ? item.borough : ""}</span>
          <span className="text-right tabular-nums">
            {!ctx.room && item.rent !== null ? formatRent(item.rent) : ""}
          </span>
          {!ctx.room && item.label && item.label !== "neighbourhood" && (
            <span className="col-span-2 justify-self-end">
              <Badge label={item.label} />
            </span>
          )}
        </summary>
        <div className="flex flex-col gap-4 border-t border-line px-4 pt-3 pb-4 text-sm leading-relaxed">
          <CommuteDetail r={commute} ctx={ctx} minutes={item.minutes} />
          <RentDetail e={rentEntry} ctx={ctx} />
        </div>
      </details>
    </li>
  );
}

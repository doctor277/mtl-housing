// One shortlist card (name, commute, rent, reliability badge). Tapping it opens the detail
// panel in place: commute (median, range, buildings, flags, source) and rent (estimate,
// CMHC basis, source, data dates). A native <details>, so it needs no JavaScript.
import { type CampusMeta, type CampusResult, type CommuteFile, commuteTarget, formatTime, windowLabel } from "@/lib/commute";
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
  campusMeta: CampusMeta;
  commuteMeta: CommuteFile["meta"];
  rentMeta: RentMeta;
  sizeLabel: string;
  room: boolean;
}

function signedMin(adj: number): string {
  return `${adj > 0 ? "+" : "−"}${Math.abs(adj)} min`;
}

function CommuteDetail({ r, ctx, minutes }: { r: CampusResult; ctx: CardContext; minutes: number }) {
  const max = ctx.commuteMeta.max_trip_min;
  const dests = ctx.campusMeta.destinations;
  const lines: string[] = [
    t.median(minutes, commuteTarget(ctx.campus, ctx.campusMeta), windowLabel(ctx.commuteMeta)),
    t.range(formatTime(r, "p10", max), formatTime(r, "p90", max)),
  ];
  if (dests.length > 1) {
    for (const d of dests) {
      const b = r.by_destination[d.id];
      if (!b) continue;
      const access = d.access_adjustment_min ? t.buildingAccess(signedMin(d.access_adjustment_min)) : "";
      const time = formatTime(b, "median", max) + access;
      // A building that is never the faster one just shows its time.
      lines.push(
        b.fastest_share
          ? t.building(d.name, time, `${Math.round(b.fastest_share * 100)}%`)
          : t.buildingTime(d.name, time),
      );
    }
  } else if (dests[0]?.access_adjustment_min) {
    lines.push(t.accessIncluded(signedMin(dests[0].access_adjustment_min)));
  }
  if (r.flags.includes("low_sample")) lines.push(t.lowSample(r.n_points));
  if (r.flags.includes("many_unreachable") && r.unreachable_share !== null) {
    lines.push(t.manyUnreachable(`${Math.round(r.unreachable_share * 100)}%`));
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

function Badge({ entry }: { entry: { label: RentEntry["label"] } }) {
  // "Estimate" is the normal case: plain muted text. Anything weaker gets an outline, so it
  // reads as a caveat without colour (colour is kept for data).
  const plain = entry.label === "neighbourhood";
  return (
    <span
      className={
        plain
          ? "text-sm text-ink-muted"
          : `inline-block rounded-full border px-2 text-sm leading-6 ${
              isLowReliability(entry.label) || entry.label === "none"
                ? "border-dashed border-control text-ink"
                : "border-control text-ink"
            }`
      }
    >
      {BADGES[entry.label]}
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
          {!ctx.room && item.label && (
            <span className="col-span-2 justify-self-end">
              <Badge entry={{ label: item.label }} />
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

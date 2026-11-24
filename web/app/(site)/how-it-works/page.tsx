// How it works (M4.3): where the commute times and rents come from, and how the shortlist is
// made. Short on purpose; the full sources and limitations page is M5. Every number comes from
// commute.json and rent.json; wording in lib/strings.
import type { Metadata } from "next";
import { campusOptions, departureWindow } from "@/lib/commute";
import { loadCommute, loadRent } from "@/lib/data";
import type { LabelKey } from "@/lib/rent";
import { SLIGHTLY_OVER_PCT } from "@/lib/shortlist";
import { strings } from "@/lib/strings";

const t = strings.howItWorks;

/** The caveat labels explained, in order (the plain "Estimate" needs no explanation). */
const CAVEATS: [LabelKey, keyof typeof t.rent.labels][] = [
  ["zone", "zone"],
  ["neighbourhood_low", "low"],
  ["none", "none"],
];

export const metadata: Metadata = { title: `${t.title} · ${strings.siteName}` };

function Section({ heading, id, children }: { heading: string; id?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="mt-10 scroll-mt-4">
      <h2 className="text-lg font-semibold">{heading}</h2>
      <div className="mt-3 flex flex-col gap-3">{children}</div>
    </section>
  );
}

export default async function HowItWorks() {
  const [commute, rent] = await Promise.all([loadCommute(), loadRent()]);
  const meta = commute.meta;
  const { start, end } = departureWindow(meta);
  const day = strings.format.longDate(meta.analysis_date);
  const campuses = campusOptions(commute);
  const multi = campuses.filter((c) => meta.campuses[c.key].destinations.length > 1);
  const adjustments = Object.values(meta.campuses).flatMap((c) =>
    c.destinations.filter((d) => d.access_adjustment_min !== 0),
  );
  const r = rent.meta;
  // The attribution texts the pipeline writes into the data files (DATA_SOURCES.md wording),
  // once each: both files credit the Ville de Montréal and the census file.
  const seen = new Set<string>();
  const credits = [...meta.sources, ...r.sources].filter((s) => {
    const key = s.replace("licensed under ", "");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return (
    <article className="max-w-prose leading-relaxed">
      <h1 className="text-2xl leading-tight font-semibold tracking-tight sm:text-3xl">{t.title}</h1>
      <p className="mt-3 text-ink-muted">{t.lead}</p>

      <Section heading={t.commute.heading}>
        <p>{t.commute.doorToDoor}</p>
        <p>{t.commute.schedule(start, end, day)}</p>
        <p>{t.commute.range}</p>
        <p>{t.commute.walking(meta.walk_speed_kmh)}</p>
        {multi.map((c) => (
          <p key={c.key}>
            {t.commute.closest(c.label, strings.format.andList(meta.campuses[c.key].destinations.map((d) => d.name)))}
          </p>
        ))}
        {adjustments.length > 0 && (
          <>
            <p>{t.commute.adjustmentsLead}</p>
            <ul role="list" className="list-disc pl-5">
              {adjustments.map((d) => (
                <li key={d.id} className="tabular-nums">
                  {t.commute.adjustment(d.name, strings.map.popup.signedMin(d.access_adjustment_min))}
                </li>
              ))}
            </ul>
          </>
        )}
        <p>{t.commute.limits}</p>
      </Section>

      <Section heading={t.rent.heading}>
        <p>{t.rent.method(r.cmhc.period, r.statcan.quarter)}</p>
        <p>{t.rent.oldLeases}</p>
        <p>{t.rent.rounding(r.rounding.step)}</p>
        <p>{t.rent.labelsLead}</p>
        <ul role="list" className="list-disc pl-5">
          {CAVEATS.map(([label, key]) => (
            <li key={label}>
              <span className="font-semibold">{strings.rent.badges[label]}</span>: {t.rent.labels[key]}
            </li>
          ))}
        </ul>
        <p>{strings.rent.roomLine(r)}</p>
      </Section>

      <Section heading={t.shortlist.heading}>
        <p>{t.shortlist.maxCommute}</p>
        <p>{t.shortlist.budget(SLIGHTLY_OVER_PCT)}</p>
        <p>{t.shortlist.noBudget}</p>
        <p>{t.shortlist.rooms}</p>
      </Section>

      {/* The footer's "Sources" link points here until M5's sources page. */}
      <Section heading={t.data.heading} id="data-and-credits">
        <p className="text-sm text-ink-muted">{strings.rent.dataLine(r)}</p>
        <ul role="list" className="flex flex-col gap-2 text-sm text-ink-muted">
          {credits.map((a) => (
            <li key={a}>{a}</li>
          ))}
          <li>
            <a
              href="https://creativecommons.org/licenses/by/4.0/"
              className="inline-flex min-h-11 items-center font-semibold text-link underline"
            >
              {t.data.licence}
            </a>
          </li>
        </ul>
        <p className="text-sm text-ink-muted">{t.data.more}</p>
      </Section>
    </article>
  );
}

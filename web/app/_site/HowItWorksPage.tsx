// How it works (M4.3): where the commute times and rents come from, and how the shortlist is
// made. Short on purpose; sources, credits and limitations are on the sources page (M5.2).
// Every number comes from commute.json and rent.json; wording in lib/strings, in each language
// (M5.3b).
import Link from "next/link";
import { campusOptions, departureWindow } from "@/lib/commute";
import { loadCommute, loadRent } from "@/lib/data";
import { inLang, type Lang } from "@/lib/localized";
import type { LabelKey } from "@/lib/rent";
import { PATHS } from "@/lib/routes";
import { SLIGHTLY_OVER_PCT } from "@/lib/shortlist";
import { getStrings } from "@/lib/strings";
import { hitAreaLink } from "./linkStyles";
import Section from "./Section";

/** The caveat labels explained, in order (the plain "Estimate" needs no explanation). */
const CAVEATS: [LabelKey, "zone" | "low" | "none"][] = [
  ["zone", "zone"],
  ["neighbourhood_low", "low"],
  ["none", "none"],
];

export default async function HowItWorksPage({ lang }: { lang: Lang }) {
  const s = getStrings(lang);
  const t = s.howItWorks;
  const [commute, rent] = await Promise.all([loadCommute(), loadRent()]);
  const meta = commute.meta;
  const { start, end } = departureWindow(meta, s);
  const day = s.format.longDate(meta.analysis_date);
  const campuses = campusOptions(commute, s);
  const multi = campuses.filter((c) => meta.campuses[c.key].destinations.length > 1);
  const adjustments = Object.values(meta.campuses).flatMap((c) =>
    c.destinations.filter((d) => d.access_adjustment_min !== 0),
  );
  const r = rent.meta;

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
            {t.commute.closest(
              c.label,
              s.format.andList(meta.campuses[c.key].destinations.map((d) => inLang(d.name, lang))),
            )}
          </p>
        ))}
        {adjustments.length > 0 && (
          <>
            <p>{t.commute.adjustmentsLead}</p>
            <ul role="list" className="list-disc pl-5">
              {adjustments.map((d) => (
                <li key={d.id} className="tabular-nums">
                  {t.commute.adjustment(inLang(d.name, lang), s.map.popup.signedMin(d.access_adjustment_min))}
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
              <span className="font-semibold">{s.rent.badges[label]}</span>
              {s.format.colon}
              {t.rent.labels[key]}
            </li>
          ))}
        </ul>
        <p>{s.rent.roomLine(r)}</p>
      </Section>

      <Section heading={t.shortlist.heading}>
        <p>{t.shortlist.maxCommute}</p>
        <p>{t.shortlist.budget(SLIGHTLY_OVER_PCT)}</p>
        <p>{t.shortlist.noBudget}</p>
        <p>{t.shortlist.rooms}</p>
      </Section>

      {/* One line pointing to the sources page, which has the credits (owner, M5 decision 13). */}
      <p className="mt-10">
        {t.sources.text}{" "}
        <Link href={PATHS[lang].sources} className={hitAreaLink}>
          {t.sources.link}
        </Link>
      </p>
    </article>
  );
}

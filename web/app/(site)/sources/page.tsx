// Sources and limitations (M5.2, owner's M5 decisions 11–14): the three required limitations,
// the validation summary, the commute and rent limits, every source with its link, licence and
// date, the credits, and the About block. Numbers come from commute.json and rent.json, or from
// lib/sources.ts (checked by its test against the files it cites); wording in lib/strings.
import type { Metadata } from "next";
import { campusOptions, departureWindow } from "@/lib/commute";
import { loadCommute, loadRent } from "@/lib/data";
import { LICENCE_URLS, QUARTIERS_DOWNLOADED, SOURCES, type SourceId, VALIDATION, VALIDATION_FILE } from "@/lib/sources";
import { strings } from "@/lib/strings";
import { hitAreaLink } from "../linkStyles";
import Section from "../Section";

const t = strings.sources;

export const metadata: Metadata = { title: `${t.title} · ${strings.siteName}` };

function Limitation({ heading, children }: { heading: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="font-semibold">{heading}</h3>
      <p className="mt-1">{children}</p>
    </div>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul role="list" className="flex list-disc flex-col gap-2 pl-5">
      {items.map((i) => (
        <li key={i}>{i}</li>
      ))}
    </ul>
  );
}

export default async function SourcesPage() {
  const [commute, rent] = await Promise.all([loadCommute(), loadRent()]);
  const meta = commute.meta;
  const r = rent.meta;
  const { start, end } = departureWindow(meta);
  const day = strings.format.longDate(meta.analysis_date);
  const date = strings.format.date;
  const campusLabel = Object.fromEntries(campusOptions(commute).map((c) => [c.key, c.label]));
  const feed = (name: string) => meta.gtfs_feeds.find((f) => f.name === name);

  // Each source's date, from the data files (the Ville de Montréal's from the manifest).
  const d = t.list.dates;
  const feedDate = (name: string) => {
    const f = feed(name);
    return f ? d.feed(date(f.start), date(f.end)) : null;
  };
  const dates: Record<SourceId, string | null> = {
    stm: feedDate("stm"),
    rem: feedDate("rem"),
    exo: feedDate("exo_trains"),
    osm: d.osm(date(meta.osm_date)),
    quartiers: d.downloaded(date(QUARTIERS_DOWNLOADED)),
    census: d.census,
    cmhc: d.cmhc(r.cmhc.period),
    statcanRent: d.statcanRent(r.statcan.quarter, date(r.statcan.released)),
  };
  const groups: [string, SourceId[]][] = [
    [t.list.commuteHeading, ["stm", "rem", "exo", "osm", "quartiers", "census"]],
    [t.list.rentHeading, ["cmhc", "statcanRent"]],
  ];

  // The attribution texts the pipeline writes into the data files (DATA_SOURCES.md wording),
  // once each: both files credit the Ville de Montréal and the census file. rent.json first:
  // its Ville de Montréal line has the full "licensed under CC BY 4.0" wording.
  const seen = new Set<string>();
  const credits = [...r.sources, ...meta.sources].filter((s) => {
    const key = s.replace("licensed under ", "");
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  const v = VALIDATION;
  return (
    <article className="max-w-prose leading-relaxed">
      <h1 className="text-2xl leading-tight font-semibold tracking-tight sm:text-3xl">{t.title}</h1>
      <p className="mt-3 text-ink-muted">{t.lead}</p>

      <Section heading={t.limits.heading} id="limitations">
        <Limitation heading={t.limits.oldLeases.heading}>{t.limits.oldLeases.text}</Limitation>
        <Limitation heading={t.limits.concordiaEast.heading}>
          {t.limits.concordiaEast.text(v.concordiaPeelWalk)}
        </Limitation>
        <Limitation heading={t.limits.firstWait.heading}>
          {t.limits.firstWait.text(v.mcgillRoute5.ours, v.mcgillRoute5.google, start, end)}
        </Limitation>
      </Section>

      <Section heading={t.validation.heading} id="validation">
        <p>{t.validation.method(strings.format.longDate(v.googleDate), v.rule.pct, v.rule.minMinutes)}</p>
        <Bullets
          items={(Object.keys(v.passed) as (keyof typeof v.passed)[]).map((c) =>
            t.validation.campus(campusLabel[c] ?? c, v.passed[c].pass, v.passed[c].total),
          )}
        />
        <p>{t.validation.udemBuildings}</p>
        <p>{t.validation.udemRoute4(v.udemRoute4.googleFirst, v.udemRoute4.googleLikeForLike, v.udemRoute4.ours)}</p>
        <p>{t.validation.udemRoute3(v.udemRoute3.googleFirst, v.udemRoute3.googleFastest, v.udemRoute3.ours)}</p>
        <p>{t.validation.mcgillRoute5}</p>
        <p>{t.validation.inSample}</p>
        <p className="text-sm text-ink-muted">
          {t.validation.cite(VALIDATION_FILE, date(v.googleCollected.udem), date(v.googleCollected.others))}
        </p>
      </Section>

      <Section heading={t.commute.heading} id="commute-limits">
        <Bullets
          items={[
            t.commute.oneMorning(start, end, day),
            t.commute.delays,
            t.commute.flatWalking(meta.walk_speed_kmh),
            t.commute.transfers,
            t.commute.buildings,
            t.commute.census,
            t.commute.maxTrip(meta.max_trip_min),
          ]}
        />
        {meta.out_of_scope.length > 0 && (
          <>
            <p>{t.commute.outOfScopeLead}</p>
            <Bullets items={meta.out_of_scope.map((o) => o.reason)} />
          </>
        )}
      </Section>

      <Section heading={t.rent.heading} id="rent-limits">
        <Bullets
          items={[
            t.rent.method(r.cmhc.period, r.statcan.quarter),
            t.rent.experimental,
            t.rent.coverage,
            t.rent.rooms(strings.format.rent(r.room.estimate), r.statcan.quarter),
          ]}
        />
        <p>{t.rent.crosswalkLead}</p>
        <Bullets items={r.crosswalk_notes.map((n) => t.rent.crosswalkNote(n.quartier_name, n.text))} />
      </Section>

      <Section heading={t.list.heading} id="sources">
        <p>{t.list.lead}</p>
        {groups.map(([heading, ids]) => (
          <div key={heading}>
            <h3 className="font-semibold">{heading}</h3>
            <ul role="list" className="mt-2 flex flex-col gap-4">
              {ids.map((id) => {
                const s = SOURCES.find((x) => x.id === id)!;
                const item: { name: string; publisher: string; publisherUrl?: string; note?: string } =
                  t.list.items[id];
                return (
                  <li key={id}>
                    <a href={s.url} className={hitAreaLink}>
                      {item.name}
                    </a>
                    <span className="block text-sm text-ink-muted">
                      {item.publisherUrl ? (
                        <a href={item.publisherUrl} className="text-link underline">
                          {item.publisher}
                        </a>
                      ) : (
                        item.publisher
                      )}
                      . {dates[id]} {t.list.licenceLabel}{" "}
                      <a href={LICENCE_URLS[s.licence]} className="text-link underline">
                        {t.list.licence[s.licence]}
                      </a>
                      .
                    </span>
                    {item.note && <span className="block text-sm text-ink-muted">{item.note}</span>}
                  </li>
                );
              })}
            </ul>
          </div>
        ))}
        <p className="text-sm text-ink-muted">{t.list.creditsLead}</p>
        <ul role="list" className="flex flex-col gap-2 text-sm text-ink-muted">
          {credits.map((a) => (
            <li key={a}>{a}</li>
          ))}
        </ul>
      </Section>

      <Section heading={t.about.heading} id="about">
        <p>{t.about.notAffiliated}</p>
        <p>{t.about.contact(strings.contactEmail)}</p>
      </Section>
    </article>
  );
}

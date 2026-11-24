"use client";

// /map: every neighbourhood, with Commute/Rent, campus and size pickers and the legend. Its
// look is still the M2.6/M3 one; the results' map view (M4.3) is app/(site)/results/ResultsMap.tsx.
// Wording: lib/strings.

import { type CSSProperties, useState } from "react";
import { type CommuteFile, campusOptions, commuteTarget, windowLabel } from "@/lib/commute";
import { BIN_UPPER_MIN, COMMUTE_COLOURS, NO_DATA_COLOUR, NO_RESIDENTS_COLOUR, OVER_MAX_COLOUR } from "@/lib/legend";
import {
  BIN_PCT,
  binEdges,
  DEFAULT_SIZE,
  RENT_COLOURS,
  RENT_FILL_OPACITY,
  RENT_NO_DATA_COLOUR,
  type RentFile,
  SIZES,
  type ShownSize,
} from "@/lib/rent";
import { strings } from "@/lib/strings";
import QuartierMap, { type Mode } from "./QuartierMap";

const t = strings.map;

const swatch = (background: string, extra: CSSProperties = {}) => (
  <span
    style={{
      background,
      display: "inline-block",
      width: 14,
      height: 10,
      marginRight: 4,
      verticalAlign: "middle",
      boxShadow: "inset 0 0 0 1px #888", // so the near-white class still shows
      ...extra,
    }}
  />
);

const HATCH_CSS =
  "repeating-linear-gradient(135deg, #141414 0 2px, #ffffff 2px 3px, transparent 3px 8px), #f3f2ee";

function Toggle<T extends string>({
  options,
  value,
  onChange,
  label,
}: {
  options: { key: T; label: string }[];
  value: T;
  onChange: (v: T) => void;
  label: string;
}) {
  return (
    <div role="group" aria-label={label} style={{ display: "flex", gap: 4, marginBottom: 6 }}>
      {options.map((o) => (
        <button
          key={o.key}
          type="button"
          aria-pressed={o.key === value}
          onClick={() => onChange(o.key)}
          style={{
            padding: "2px 8px",
            border: "1px solid #555",
            background: o.key === value ? "#222" : "white",
            color: o.key === value ? "white" : "black",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function CommuteLegend({ commute, campus }: { commute: CommuteFile | null; campus: string }) {
  const meta = commute?.meta.campuses[campus];
  if (!commute || !meta) return <div>{t.loadingCommutes}</div>;
  const max = commute.meta.max_trip_min;
  const labels = strings.commute.classLabels(BIN_UPPER_MIN, max);
  return (
    <>
      <b>{t.commuteTitle(meta.name)}</b>
      <br />
      {commuteTarget(campus, meta)}, {windowLabel(commute.meta)}
      {COMMUTE_COLOURS.map((colour, i) => (
        <div key={colour}>
          {swatch(colour)}
          {labels[i]}
        </div>
      ))}
      <div>
        {swatch(OVER_MAX_COLOUR)}
        {t.overMaxClass(max)}
      </div>
      <div>
        {swatch(NO_DATA_COLOUR)}
        {t.noData}
      </div>
    </>
  );
}

function RentLegend({ rent, size }: { rent: RentFile | null; size: ShownSize }) {
  if (!rent) return <div>{t.loadingRents}</div>;
  const step = rent.meta.rounding.step;
  const level = rent.meta.montreal[size].statcan_asking;
  const ranges = strings.rent.classRanges(binEdges(level, step), step);
  const pct = strings.rent.classPct(BIN_PCT);
  return (
    <>
      <b>{t.rentTitle(strings.rent.sizeLabel(size))}</b>
      <br />
      {t.rentBasis(level)}
      {RENT_COLOURS.map((colour, i) => (
        <div key={colour}>
          {swatch(colour, { opacity: RENT_FILL_OPACITY })}
          {t.rentClass(pct[i], ranges[i])}
        </div>
      ))}
      <div>
        {swatch("", { background: HATCH_CSS })}
        {t.lowReliability}
      </div>
      <div>
        {swatch(RENT_NO_DATA_COLOUR)}
        {t.notEnoughData}
      </div>
      <div style={{ marginTop: 4, fontSize: 11 }}>{strings.rent.roomLine(rent.meta)}</div>
      <div style={{ marginTop: 4, fontSize: 11 }}>{strings.rent.sourceLine}</div>
      <div style={{ marginTop: 4, fontSize: 11 }}>{strings.rent.dataLine(rent.meta)}</div>
    </>
  );
}

export default function MapView() {
  const [mode, setMode] = useState<Mode>("commute");
  const [size, setSize] = useState<ShownSize>(DEFAULT_SIZE);
  const [chosenCampus, setCampus] = useState("udem");
  const [commute, setCommute] = useState<CommuteFile | null>(null);
  // Fall back to the first campus in commute.json if the chosen one isn't there.
  const campus =
    commute && !(chosenCampus in commute.meta.campuses)
      ? (Object.keys(commute.meta.campuses)[0] ?? chosenCampus)
      : chosenCampus;
  const [rent, setRent] = useState<RentFile | null>(null);
  const [legendOpen, setLegendOpen] = useState(true); // on a phone the legend hides half the map

  return (
    <main style={{ position: "relative", height: "100vh" }}>
      <QuartierMap
        mode={mode}
        size={size}
        campus={campus}
        onDataLoaded={(c, r) => {
          setCommute(c);
          setRent(r);
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 8,
          left: 8,
          maxWidth: "min(360px, calc(100vw - 16px))",
          maxHeight: "calc(100vh - 16px)",
          overflowY: "auto",
          background: "white",
          color: "black",
          padding: 8,
          fontSize: 13,
          border: "1px solid #999",
        }}
      >
        <Toggle
          label={t.group}
          options={[
            { key: "commute", label: t.modes.commute },
            { key: "rent", label: t.modes.rent },
          ]}
          value={mode}
          onChange={setMode}
        />
        {mode === "commute" && commute && (
          // Only campuses present in commute.json are offered.
          <Toggle label={t.campus} options={campusOptions(commute)} value={campus} onChange={setCampus} />
        )}
        {mode === "rent" && (
          <Toggle
            label={t.size}
            options={SIZES.map((key) => ({ key, label: strings.rent.sizeLabel(key) }))}
            value={size}
            onChange={setSize}
          />
        )}
        <button
          type="button"
          aria-expanded={legendOpen}
          onClick={() => setLegendOpen(!legendOpen)}
          style={{
            display: "block",
            fontSize: 12,
            padding: "1px 6px",
            marginBottom: 6,
            border: "1px solid #555",
            background: "white",
            cursor: "pointer",
          }}
        >
          {legendOpen ? t.hideLegend : t.showLegend}
        </button>
        {legendOpen && (
          <>
            {mode === "commute" ? <CommuteLegend commute={commute} campus={campus} /> : <RentLegend rent={rent} size={size} />}
            <div>
              {swatch(NO_RESIDENTS_COLOUR, { outline: "1.5px dashed #333", outlineOffset: -1 })}
              {t.noResidents}
            </div>
            <div style={{ marginTop: 4, fontSize: 11 }}>
              {t.clickHint} {t.attribution(mode === "rent")}
            </div>
          </>
        )}
      </div>
    </main>
  );
}

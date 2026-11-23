"use client";

// The map plus its controls and legend. Commute/Rent toggle, size picker (rent only).

import { type CSSProperties, useState } from "react";
import { BINS, NO_DATA_COLOUR, NO_RESIDENTS_COLOUR, OVER_MAX_COLOUR } from "@/lib/legend";
import {
  type BedroomType,
  binEdges,
  binLegend,
  DEFAULT_SIZE,
  formatRent,
  RENT_BINS,
  RENT_NO_DATA_COLOUR,
  type RentFile,
  roomLine,
  SIZES,
  sourceLine,
} from "@/lib/rent";
import QuartierMap, { type Mode } from "./QuartierMap";

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

function CommuteLegend() {
  return (
    <>
      <b>Median transit commute to UdeM</b>
      <br />
      fastest UdeM building, leaving 7:30–8:30, Tue 2026-12-01
      {BINS.map(([label, colour]) => (
        <div key={label}>
          {swatch(colour)}
          {label}
        </div>
      ))}
      <div>
        {swatch(OVER_MAX_COLOUR)}&gt; 120 min
      </div>
      <div>
        {swatch(NO_DATA_COLOUR)}no data
      </div>
    </>
  );
}

function RentLegend({ rent, size }: { rent: RentFile | null; size: BedroomType }) {
  if (!rent) return <div>Loading rents…</div>;
  const step = rent.meta.rounding.step;
  const level = rent.meta.montreal[size].statcan_asking;
  const ranges = binLegend(binEdges(level, step), step);
  const label = SIZES.find((s) => s.key === size)?.label ?? size;
  return (
    <>
      <b>Estimated rent, {label}</b>
      <br />
      compared with the Montréal asking rent ({formatRent(level)})
      {RENT_BINS.map(([pct, colour], i) => (
        <div key={pct}>
          {swatch(colour)}
          {pct}: {ranges[i]}
        </div>
      ))}
      <div>
        {swatch("", { background: HATCH_CSS })}low reliability (CMHC: “use with caution”)
      </div>
      <div>
        {swatch(RENT_NO_DATA_COLOUR)}not enough data
      </div>
      <div style={{ marginTop: 4, fontSize: 11 }}>{roomLine(rent.meta)}</div>
      <div style={{ marginTop: 4, fontSize: 11 }}>{sourceLine(rent.meta)}</div>
    </>
  );
}

export default function MapView() {
  const [mode, setMode] = useState<Mode>("commute");
  const [size, setSize] = useState<BedroomType>(DEFAULT_SIZE);
  const [rent, setRent] = useState<RentFile | null>(null);
  const [legendOpen, setLegendOpen] = useState(true); // on a phone the legend hides half the map

  return (
    <main style={{ position: "relative", height: "100vh" }}>
      <QuartierMap mode={mode} size={size} onRentLoaded={setRent} />
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
          label="Map"
          options={[
            { key: "commute", label: "Commute" },
            { key: "rent", label: "Rent" },
          ]}
          value={mode}
          onChange={setMode}
        />
        {mode === "rent" && <Toggle label="Size" options={SIZES} value={size} onChange={setSize} />}
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
          {legendOpen ? "Hide legend" : "Show legend"}
        </button>
        {legendOpen && (
          <>
            {mode === "commute" ? <CommuteLegend /> : <RentLegend rent={rent} size={size} />}
            <div>
              {swatch(NO_RESIDENTS_COLOUR, { outline: "1.5px dashed #333", outlineOffset: -1 })}no
              residents (park)
            </div>
            <div style={{ marginTop: 4, fontSize: 11 }}>
              Click a neighbourhood for details. Quartiers: Ville de Montréal (CC BY 4.0).
              Schedules: STM, REM, exo (CC BY 4.0).{" "}
              {mode === "rent" && "Rents: CMHC, Statistics Canada. "}Map data © OpenStreetMap
              contributors.
            </div>
          </>
        )}
      </div>
    </main>
  );
}

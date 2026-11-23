"use client";

// Quartiers coloured by median UdeM transit commute (fastest UdeM building) or by the
// estimated rent for one size. Still the Phase 1.5 "ugly map": no styling, no form, no
// ranking (those come in M4).

import { useEffect, useRef, useState } from "react";
import type { ExpressionSpecification, Map as MlMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { type CommuteFile, featureProps, formatTime } from "@/lib/commute";
import {
  BIN_UPPER_MIN,
  BINS,
  NO_DATA_COLOUR,
  NO_RESIDENTS_COLOUR,
  OVER_MAX_COLOUR,
} from "@/lib/legend";
import {
  BADGES,
  type BedroomType,
  detailLine,
  extraLines,
  formatRent,
  RENT_BINS,
  RENT_NO_DATA_COLOUR,
  type RentFile,
  rentFeatureProps,
  SIZES,
  sourceLine,
} from "@/lib/rent";

export type Mode = "commute" | "rent";

const CAMPUS = "udem";
const BASEMAP = "https://tiles.openfreemap.org/styles/positron";
const HATCH = "low-reliability-hatch";

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

interface QuartierProps {
  id: string;
  name: string;
  borough: string;
  no_residents?: boolean;
  part_of?: string;
}

function commutePopup(props: QuartierProps, commute: CommuteFile): string {
  const max = commute.meta.max_trip_min;
  const r = commute.results[props.id]?.[CAMPUS];
  if (!r) return "no data";
  const lines = [
    `fastest UdeM building, median: <b>${formatTime(r, "median", max)}</b>`,
    `p10–p90: ${formatTime(r, "p10", max)} – ${formatTime(r, "p90", max)}`,
  ];
  for (const d of commute.meta.campuses[CAMPUS].destinations) {
    const b = r.by_destination[d.id];
    if (!b) continue;
    const share = b.fastest_share === null ? "?" : `${Math.round(b.fastest_share * 100)}%`;
    const adj = d.access_adjustment_min;
    const access = adj ? ` (incl. ${adj > 0 ? "+" : "−"}${Math.abs(adj)} min access adjustment)` : "";
    lines.push(
      `${escapeHtml(d.name)}: ${formatTime(b, "median", max)}${access}, fastest for ${share} of homes`,
    );
  }
  lines.push(`${r.n_points} sample points, ${r.n_unreachable} unreachable`);
  lines.push(`flags: ${r.flags.length ? r.flags.join(", ") : "none"}`);
  return lines.join("<br>");
}

function rentPopup(props: QuartierProps, rent: RentFile, size: BedroomType): string {
  const sizeLabel = SIZES.find((s) => s.key === size)?.label ?? size;
  const e = rent.results[props.id]?.[size];
  if (!e) return `${sizeLabel}: not enough data`;
  const value = e.estimate === null ? "" : `<b>${formatRent(e.estimate)}</b> a month · `;
  const lines = [
    `${escapeHtml(sizeLabel)}: ${value}<i>${BADGES[e.label]}</i>`,
    escapeHtml(detailLine(e, rent.meta)),
    ...extraLines(e, rent.meta).map(escapeHtml),
  ];
  if (e.estimate !== null) {
    lines.push(`<small>${escapeHtml(sourceLine(rent.meta))}</small>`);
  }
  return lines.join("<br>");
}

function popupHtml(
  props: QuartierProps,
  mode: Mode,
  size: BedroomType,
  commute: CommuteFile,
  rent: RentFile,
  names: Map<string, string>,
): string {
  const head = `<b>${escapeHtml(props.name)}</b> (${escapeHtml(props.borough)})<br>`;
  if (props.no_residents) {
    const parent = names.get(props.part_of ?? "") ?? props.part_of ?? "?";
    const what = mode === "rent" ? "rent estimate" : "commute time";
    return (
      head +
      `No residents, so no ${what} is shown.<br>` +
      `In the city's data this area is part of the ${escapeHtml(parent)} quartier.`
    );
  }
  return head + (mode === "rent" ? rentPopup(props, rent, size) : commutePopup(props, commute));
}

/** 8×8 diagonal hatch: a dark and a light line side by side, so it shows on pale and
 * dark classes alike. */
function hatchImage(): { width: number; height: number; data: Uint8Array } {
  const n = 8;
  const data = new Uint8Array(n * n * 4);
  for (let y = 0; y < n; y++) {
    for (let x = 0; x < n; x++) {
      const d = (x + y) % n;
      const o = (y * n + x) * 4;
      if (d === 0 || d === 1) data.set([20, 20, 20, 200], o);
      else if (d === 2) data.set([255, 255, 255, 200], o);
    }
  }
  return { width: n, height: n, data };
}

function rentColour(size: BedroomType): ExpressionSpecification {
  const bin = ["get", `rent_bin_${size}`];
  return [
    "case",
    ["==", ["coalesce", ["get", "no_residents"], false], true],
    NO_RESIDENTS_COLOUR,
    ["<", bin, 0],
    RENT_NO_DATA_COLOUR,
    ["match", bin, ...RENT_BINS.flatMap(([, colour], i) => [i, colour]), RENT_NO_DATA_COLOUR],
  ] as unknown as ExpressionSpecification;
}

const lowFilter = (size: BedroomType): ExpressionSpecification => [
  "==",
  ["get", `rent_low_${size}`],
  true,
];

export default function QuartierMap({
  mode,
  size,
  onRentLoaded,
}: {
  mode: Mode;
  size: BedroomType;
  onRentLoaded: (rent: RentFile) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The click handler is registered once; it reads the current choice from here.
  const view = useRef({ mode, size });
  useEffect(() => {
    view.current = { mode, size };
  }, [mode, size]);

  useEffect(() => {
    let map: MlMap | undefined;
    let cancelled = false;

    (async () => {
      const maplibregl = await import("maplibre-gl");
      maplibregl.setWorkerUrl(
        new URL("maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url).toString(),
      );
      const [geo, commute, rent] = await Promise.all([
        fetch("/data/neighbourhoods.geojson").then((r) => r.json()),
        fetch("/data/commute.json").then((r) => r.json() as Promise<CommuteFile>),
        fetch("/data/rent.json").then((r) => r.json() as Promise<RentFile>),
      ]);
      if (cancelled || !container.current) return;
      onRentLoaded(rent);

      const names = new Map<string, string>();
      for (const f of geo.features) {
        const p = f.properties as QuartierProps;
        names.set(p.id, p.name);
        Object.assign(
          p,
          p.no_residents
            ? { status: "no_residents" }
            : {
                ...featureProps(commute.results[p.id]?.[CAMPUS]),
                ...rentFeatureProps(rent.results[p.id], rent.meta),
              },
        );
      }

      map = new maplibregl.Map({
        container: container.current,
        style: BASEMAP,
        center: [-73.72, 45.55],
        zoom: 10,
      });
      mapRef.current = map;

      map.on("load", () => {
        if (!map) return;
        map.addSource("quartiers", { type: "geojson", data: geo });
        map.addImage(HATCH, hatchImage());

        // ["step", input, colour0, edge1, colour1, ...]; built in a loop, so TS can't
        // check the tuple shape.
        const step = [
          "step",
          ["get", "median"],
          BINS[0][1],
          ...BIN_UPPER_MIN.flatMap((upper, i) => [upper + 0.5, BINS[i + 1][1]]),
        ] as unknown as ExpressionSpecification;
        const commuteColour: ExpressionSpecification = [
          "match",
          ["get", "status"],
          "ok",
          step,
          "over_max",
          OVER_MAX_COLOUR,
          "no_residents",
          NO_RESIDENTS_COLOUR,
          NO_DATA_COLOUR,
        ];
        const { mode: m, size: s } = view.current;
        map.addLayer({
          id: "commute-fill",
          type: "fill",
          source: "quartiers",
          layout: { visibility: m === "commute" ? "visible" : "none" },
          paint: { "fill-color": commuteColour, "fill-opacity": 0.6 },
        });
        map.addLayer({
          id: "rent-fill",
          type: "fill",
          source: "quartiers",
          layout: { visibility: m === "rent" ? "visible" : "none" },
          paint: { "fill-color": rentColour(s), "fill-opacity": 0.8 },
        });
        map.addLayer({
          id: "rent-low-hatch",
          type: "fill",
          source: "quartiers",
          filter: lowFilter(s),
          layout: { visibility: m === "rent" ? "visible" : "none" },
          paint: { "fill-pattern": HATCH },
        });
        map.addLayer({
          id: "quartiers-line",
          type: "line",
          source: "quartiers",
          paint: { "line-color": "#333", "line-width": 0.5 },
        });
        // Second cue for "no residents" (its grey is close to the rent map's neutral).
        map.addLayer({
          id: "no-residents-line",
          type: "line",
          source: "quartiers",
          filter: ["==", ["coalesce", ["get", "no_residents"], false], true],
          paint: { "line-color": "#333", "line-width": 1.5, "line-dasharray": [2, 2] },
        });

        for (const d of commute.meta.campuses[CAMPUS].destinations) {
          new maplibregl.Marker()
            .setLngLat([d.lon, d.lat])
            .setPopup(new maplibregl.Popup().setText(d.name))
            .addTo(map);
        }

        for (const layer of ["commute-fill", "rent-fill"]) {
          map.on("click", layer, (e) => {
            const f = e.features?.[0];
            if (!f || !map) return;
            const { mode: cm, size: cs } = view.current;
            // Narrow enough on a phone for MapLibre's anchoring to keep it on screen
            // (a real mobile detail panel comes in M4).
            new maplibregl.Popup({ maxWidth: "min(360px, 70vw)" })
              .setLngLat(e.lngLat)
              .setHTML(popupHtml(f.properties as QuartierProps, cm, cs, commute, rent, names))
              .addTo(map);
          });
          map.on("mouseenter", layer, () => {
            if (map) map.getCanvas().style.cursor = "pointer";
          });
          map.on("mouseleave", layer, () => {
            if (map) map.getCanvas().style.cursor = "";
          });
        }
        setReady(true);
      });
    })().catch((err: unknown) => setError(String(err)));

    return () => {
      cancelled = true;
      mapRef.current = null;
      map?.remove();
    };
    // Load once; mode and size changes are applied by the effect below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const rentVis = mode === "rent" ? "visible" : "none";
    map.setLayoutProperty("commute-fill", "visibility", mode === "commute" ? "visible" : "none");
    map.setLayoutProperty("rent-fill", "visibility", rentVis);
    map.setLayoutProperty("rent-low-hatch", "visibility", rentVis);
    map.setPaintProperty("rent-fill", "fill-color", rentColour(size));
    map.setFilter("rent-low-hatch", lowFilter(size));
  }, [ready, mode, size]);

  return (
    <>
      {error && <p>Error: {error}</p>}
      <div ref={container} style={{ position: "absolute", inset: 0 }} />
    </>
  );
}

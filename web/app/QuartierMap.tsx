"use client";

// The results' map view: quartiers coloured by median transit commute to the searched campus
// or by the estimated rent for one size. Neighbourhoods outside the search are drawn without
// data colour, the popup comes from the results page, and the view fits the results.
// Wording: lib/strings. (The older /map explorer that also used this was deleted in M5.1.)

import { useEffect, useRef, useState } from "react";
import type { ExpressionSpecification, Map as MlMap, Popup } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { type CommuteFile, campusFeatureProps } from "@/lib/commute";
import { inLang } from "@/lib/localized";
import {
  BIN_UPPER_MIN,
  COMMUTE_COLOURS,
  NO_DATA_COLOUR,
  NO_RESIDENTS_COLOUR,
  NOT_IN_RESULTS_COLOUR,
  OVER_MAX_COLOUR,
} from "@/lib/legend";
import {
  RENT_COLOURS,
  RENT_FILL_OPACITY,
  RENT_NO_DATA_COLOUR,
  type RentFile,
  rentFeatureProps,
  type ShownSize,
} from "@/lib/rent";
import { strings } from "@/lib/strings";

export type Mode = "commute" | "rent";

const BASEMAP = "https://tiles.openfreemap.org/styles/positron";
/** Campus building pins: ink (the site's --color-ink), shared with the results legend. */
export const CAMPUS_MARKER_COLOUR = "#0f172a";
const HATCH = "low-reliability-hatch";
const t = strings.map;

export function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

interface QuartierProps {
  id: string;
  name: string;
  borough: string;
  no_residents?: boolean;
  part_of?: string;
}

/** The results' map view: which neighbourhoods are in the results, and their popup. */
export interface ResultsLayer {
  ids: string[];
  /** Popup HTML for a neighbourhood with residents (already escaped). */
  popupHtml: (id: string) => string;
}

function noResidentsPopup(props: QuartierProps, mode: Mode, names: Map<string, string>): string {
  const parent = names.get(props.part_of ?? "") ?? props.part_of ?? "?";
  return `${escapeHtml(t.popup.noResidents(mode))}<br>${escapeHtml(t.popup.partOf(parent))}`;
}

/** Wraps a fill colour so neighbourhoods outside the results (results view only) are grey. */
function withResults(colour: unknown[]): ExpressionSpecification {
  return [
    "case",
    ["==", ["coalesce", ["get", "in_results"], true], false],
    NOT_IN_RESULTS_COLOUR,
    colour,
  ] as unknown as ExpressionSpecification;
}

function commuteColour(campus: string): ExpressionSpecification {
  // ["step", input, colour0, edge1, colour1, ...]; built in a loop, so TS can't check the
  // tuple shape.
  const step = [
    "step",
    ["get", `median_${campus}`],
    COMMUTE_COLOURS[0],
    ...BIN_UPPER_MIN.flatMap((upper, i) => [upper + 0.5, COMMUTE_COLOURS[i + 1]]),
  ];
  return withResults([
    "case",
    ["==", ["coalesce", ["get", "no_residents"], false], true],
    NO_RESIDENTS_COLOUR,
    ["match", ["get", `status_${campus}`], "ok", step, "over_max", OVER_MAX_COLOUR, NO_DATA_COLOUR],
  ]);
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

function rentColour(size: ShownSize): ExpressionSpecification {
  const bin = ["get", `rent_bin_${size}`];
  return withResults([
    "case",
    ["==", ["coalesce", ["get", "no_residents"], false], true],
    NO_RESIDENTS_COLOUR,
    ["<", bin, 0],
    RENT_NO_DATA_COLOUR,
    ["match", bin, ...RENT_COLOURS.flatMap((colour, i) => [i, colour]), RENT_NO_DATA_COLOUR],
  ]);
}

const lowFilter = (size: ShownSize): ExpressionSpecification => [
  "all",
  ["==", ["get", `rent_low_${size}`], true],
  ["!=", ["coalesce", ["get", "in_results"], true], false],
];

/** [west, south, east, north] of some features' polygons. */
function bounds(features: { geometry: { coordinates: unknown } }[]): [number, number, number, number] | null {
  let b: [number, number, number, number] | null = null;
  const walk = (c: unknown): void => {
    if (!Array.isArray(c)) return;
    if (typeof c[0] === "number") {
      const [x, y] = c as [number, number];
      b = b ? [Math.min(b[0], x), Math.min(b[1], y), Math.max(b[2], x), Math.max(b[3], y)] : [x, y, x, y];
      return;
    }
    for (const p of c) walk(p);
  };
  for (const f of features) walk(f.geometry.coordinates);
  return b;
}

export default function QuartierMap({
  mode,
  size,
  campus,
  results,
}: {
  mode: Mode;
  size: ShownSize;
  campus: string;
  results: ResultsLayer;
}) {
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MlMap | null>(null);
  const popupRef = useRef<Popup | null>(null); // closed when the mode, size or campus changes
  const [ready, setReady] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The click handler is registered once; it reads the current choice from here.
  const view = useRef({ mode, size, campus, results });
  useEffect(() => {
    view.current = { mode, size, campus, results };
  }, [mode, size, campus, results]);

  useEffect(() => {
    let map: MlMap | undefined;
    let resizeObserver: ResizeObserver | undefined;
    let cancelled = false;

    (async () => {
      const maplibregl = await import("maplibre-gl");
      maplibregl.setWorkerUrl(new URL("maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url).toString());
      const [geo, commute, rent] = await Promise.all([
        fetch("/data/neighbourhoods.geojson").then((r) => r.json()),
        fetch("/data/commute.json").then((r) => r.json() as Promise<CommuteFile>),
        fetch("/data/rent.json").then((r) => r.json() as Promise<RentFile>),
      ]);
      if (cancelled || !container.current) return;

      const inResults = new Set(view.current.results.ids);
      const campusIds = Object.keys(commute.meta.campuses);
      const names = new Map<string, string>();
      for (const f of geo.features) {
        const p = f.properties as QuartierProps;
        names.set(p.id, p.name);
        if (!p.no_residents) {
          Object.assign(p, {
            ...campusFeatureProps(commute.results[p.id], campusIds),
            ...rentFeatureProps(rent.results[p.id], rent.meta),
            in_results: inResults.has(p.id),
          });
        }
      }

      const fit = bounds(geo.features.filter((f: { properties: QuartierProps }) => inResults.has(f.properties.id)));
      map = new maplibregl.Map({
        container: container.current,
        style: BASEMAP,
        center: [-73.72, 45.55],
        zoom: 10,
      });
      mapRef.current = map;
      // Follow the container, not only the window: on a phone, 60vh changes as the address
      // bar shows and hides, and a canvas left at the old size paints only part of the frame.
      resizeObserver = new ResizeObserver(() => map?.resize());
      resizeObserver.observe(container.current);

      map.on("load", () => {
        if (!map) return;
        // Results view: show every result. Fitted here, once the map knows its own size.
        if (fit) {
          map.resize();
          map.fitBounds(fit, { padding: 24, maxZoom: 13, animate: false });
        }
        map.addSource("quartiers", { type: "geojson", data: geo });
        map.addImage(HATCH, hatchImage());

        const { mode: m, size: s, campus: c } = view.current;
        map.addLayer({
          id: "commute-fill",
          type: "fill",
          source: "quartiers",
          layout: { visibility: m === "commute" ? "visible" : "none" },
          paint: { "fill-color": commuteColour(c), "fill-opacity": 0.6 },
        });
        map.addLayer({
          id: "rent-fill",
          type: "fill",
          source: "quartiers",
          layout: { visibility: m === "rent" ? "visible" : "none" },
          paint: { "fill-color": rentColour(s), "fill-opacity": RENT_FILL_OPACITY },
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
        // The results stand out from the greyed rest by a firmer outline as well as colour.
        map.addLayer({
          id: "results-line",
          type: "line",
          source: "quartiers",
          filter: ["==", ["get", "in_results"], true],
          paint: { "line-color": "#0f172a", "line-width": 1.5 },
        });

        // Only the searched campus is marked.
        const meta = commute.meta.campuses[c];
        if (meta) {
          for (const d of meta.destinations) {
            // Ink, not MapLibre's teal (blue is for links and the rent map's cheaper classes);
            // smaller, so UdeM's two buildings stay two pins at phone zoom.
            new maplibregl.Marker({ color: CAMPUS_MARKER_COLOUR, scale: 0.7 })
              .setLngLat([d.lon, d.lat])
              .setPopup(
                new maplibregl.Popup().setText(t.marker(inLang(meta.name, strings.lang), inLang(d.name, strings.lang))),
              )
              .addTo(map);
          }
        }

        for (const layer of ["commute-fill", "rent-fill"]) {
          map.on("click", layer, (e) => {
            const f = e.features?.[0];
            if (!f || !map) return;
            const props = f.properties as QuartierProps;
            const { mode: cm, results: rs } = view.current;
            // The borough only when it differs from the name, as on the cards.
            const borough = props.borough !== props.name ? ` (${escapeHtml(props.borough)})` : "";
            const head = `<b>${escapeHtml(props.name)}</b>${borough}<br>`;
            const body = props.no_residents ? noResidentsPopup(props, cm, names) : rs.popupHtml(props.id);
            // Never wider than the map minus a margin, and panned into view if it opens past
            // an edge (the map frame clips anything outside it).
            const popup = new maplibregl.Popup({ maxWidth: "min(320px, calc(100% - 32px))" })
              .setLngLat(e.lngLat)
              .setHTML(head + body)
              .addTo(map);
            popupRef.current = popup;
            const frame = container.current?.getBoundingClientRect();
            const box = popup.getElement().getBoundingClientRect();
            if (frame) {
              const m = 8;
              const dx = box.left < frame.left + m ? box.left - frame.left - m : box.right > frame.right - m ? box.right - frame.right + m : 0;
              const dy = box.top < frame.top + m ? box.top - frame.top - m : 0;
              if (dx || dy) map.panBy([dx, dy], { duration: 200 });
            }
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
      resizeObserver?.disconnect();
      mapRef.current = null;
      popupRef.current = null;
      setReady(false); // a remount must wait for the new map's layers
      map?.remove();
    };
    // Load once; mode and size changes are applied by the effect below.
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!ready || !map) return;
    const rentVis = mode === "rent" ? "visible" : "none";
    map.setLayoutProperty("commute-fill", "visibility", mode === "commute" ? "visible" : "none");
    map.setLayoutProperty("rent-fill", "visibility", rentVis);
    map.setLayoutProperty("rent-low-hatch", "visibility", rentVis);
    map.setPaintProperty("commute-fill", "fill-color", commuteColour(campus));
    map.setPaintProperty("rent-fill", "fill-color", rentColour(size));
    map.setFilter("rent-low-hatch", lowFilter(size));
    // An open popup describes the previous mode, size or campus: close it.
    popupRef.current?.remove();
    popupRef.current = null;
  }, [ready, mode, size, campus]);

  return (
    <>
      {error && <p role="alert">{t.error(error)}</p>}
      <div ref={container} style={{ position: "absolute", inset: 0 }} />
    </>
  );
}

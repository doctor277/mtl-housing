"use client";

// Phase 1.5 "ugly map": quartiers coloured by median UdeM transit commute
// (fastest UdeM building). No styling, no form, no ranking.

import { useEffect, useRef, useState } from "react";
import type { ExpressionSpecification, Map as MlMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { type CommuteFile, featureProps, formatTime } from "@/lib/commute";
import { BIN_UPPER_MIN, BINS, NO_DATA_COLOUR, OVER_MAX_COLOUR } from "@/lib/legend";

const CAMPUS = "udem";
const BASEMAP = "https://tiles.openfreemap.org/styles/positron";

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => `&#${c.charCodeAt(0)};`);
}

function popupHtml(
  props: { id: string; name: string; borough: string },
  commute: CommuteFile,
): string {
  const max = commute.meta.max_trip_min;
  const r = commute.results[props.id]?.[CAMPUS];
  const head = `<b>${escapeHtml(props.name)}</b> (${escapeHtml(props.borough)})<br>`;
  if (!r) return head + "no data";
  const lines = [
    `fastest UdeM building, median: <b>${formatTime(r, "median", max)}</b>`,
    `p10–p90: ${formatTime(r, "p10", max)} – ${formatTime(r, "p90", max)}`,
  ];
  for (const d of commute.meta.campuses[CAMPUS].destinations) {
    const b = r.by_destination[d.id];
    if (!b) continue;
    const share = b.fastest_share === null ? "?" : `${Math.round(b.fastest_share * 100)}%`;
    const penalty = d.access_penalty_min ? ` (incl. +${d.access_penalty_min} min access)` : "";
    lines.push(
      `${escapeHtml(d.name)}: ${formatTime(b, "median", max)}${penalty}, fastest for ${share} of homes`,
    );
  }
  lines.push(`${r.n_points} sample points, ${r.n_unreachable} unreachable`);
  lines.push(`flags: ${r.flags.length ? r.flags.join(", ") : "none"}`);
  return head + lines.join("<br>");
}

export default function CommuteMap() {
  const container = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let map: MlMap | undefined;
    let cancelled = false;

    (async () => {
      const maplibregl = await import("maplibre-gl");
      maplibregl.setWorkerUrl(
        new URL("maplibre-gl/dist/maplibre-gl-worker.mjs", import.meta.url).toString(),
      );
      const [geo, commute] = await Promise.all([
        fetch("/data/neighbourhoods.geojson").then((r) => r.json()),
        fetch("/data/commute.json").then((r) => r.json() as Promise<CommuteFile>),
      ]);
      if (cancelled || !container.current) return;

      for (const f of geo.features) {
        Object.assign(f.properties, featureProps(commute.results[f.properties.id]?.[CAMPUS]));
      }

      map = new maplibregl.Map({
        container: container.current,
        style: BASEMAP,
        center: [-73.72, 45.55],
        zoom: 10,
      });

      map.on("load", () => {
        if (!map) return;
        map.addSource("quartiers", { type: "geojson", data: geo });
        // ["step", input, colour0, edge1, colour1, ...]; built in a loop, so TS can't
        // check the tuple shape.
        const step = [
          "step",
          ["get", "median"],
          BINS[0][1],
          ...BIN_UPPER_MIN.flatMap((upper, i) => [upper + 0.5, BINS[i + 1][1]]),
        ] as unknown as ExpressionSpecification;
        const fillColor: ExpressionSpecification = [
          "match",
          ["get", "status"],
          "ok",
          step,
          "over_max",
          OVER_MAX_COLOUR,
          NO_DATA_COLOUR,
        ];
        map.addLayer({
          id: "quartiers-fill",
          type: "fill",
          source: "quartiers",
          paint: { "fill-color": fillColor, "fill-opacity": 0.6 },
        });
        map.addLayer({
          id: "quartiers-line",
          type: "line",
          source: "quartiers",
          paint: { "line-color": "#333", "line-width": 0.5 },
        });

        for (const d of commute.meta.campuses[CAMPUS].destinations) {
          new maplibregl.Marker()
            .setLngLat([d.lon, d.lat])
            .setPopup(new maplibregl.Popup().setText(d.name))
            .addTo(map);
        }

        map.on("click", "quartiers-fill", (e) => {
          const f = e.features?.[0];
          if (!f || !map) return;
          new maplibregl.Popup({ maxWidth: "360px" })
            .setLngLat(e.lngLat)
            .setHTML(popupHtml(f.properties as never, commute))
            .addTo(map);
        });
        map.on("mouseenter", "quartiers-fill", () => {
          if (map) map.getCanvas().style.cursor = "pointer";
        });
        map.on("mouseleave", "quartiers-fill", () => {
          if (map) map.getCanvas().style.cursor = "";
        });
      });
    })().catch((err: unknown) => setError(String(err)));

    return () => {
      cancelled = true;
      map?.remove();
    };
  }, []);

  return (
    <>
      {error && <p>Error: {error}</p>}
      <div ref={container} style={{ position: "absolute", inset: 0 }} />
    </>
  );
}

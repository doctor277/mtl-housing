// Phase 1.5 "ugly map": data on screen, nothing else.
import { BINS, NO_DATA_COLOUR, NO_RESIDENTS_COLOUR, OVER_MAX_COLOUR } from "@/lib/legend";
import CommuteMap from "./CommuteMap";

export default function Home() {
  return (
    <main style={{ position: "relative", height: "100vh" }}>
      <CommuteMap />
      <div
        style={{
          position: "absolute",
          top: 8,
          left: 8,
          background: "white",
          color: "black",
          padding: 8,
          fontSize: 13,
          border: "1px solid #999",
        }}
      >
        <b>Median transit commute to UdeM</b>
        <br />
        fastest UdeM building, leaving 7:30–8:30, Tue 2026-12-01
        {BINS.map(([label, colour]) => (
          <div key={label}>
            <span style={{ background: colour, display: "inline-block", width: 14, height: 10 }} />{" "}
            {label}
          </div>
        ))}
        <div>
          <span
            style={{ background: OVER_MAX_COLOUR, display: "inline-block", width: 14, height: 10 }}
          />{" "}
          &gt; 120 min
        </div>
        <div>
          <span
            style={{ background: NO_DATA_COLOUR, display: "inline-block", width: 14, height: 10 }}
          />{" "}
          no data
        </div>
        <div>
          <span
            style={{
              background: NO_RESIDENTS_COLOUR,
              display: "inline-block",
              width: 14,
              height: 10,
            }}
          />{" "}
          no residents (park)
        </div>
        <div style={{ marginTop: 4, fontSize: 11 }}>
          Click a quartier for details. Quartiers: Ville de Montréal (CC BY 4.0). Schedules: STM,
          REM, exo (CC BY 4.0). Map data © OpenStreetMap contributors.
        </div>
      </div>
    </main>
  );
}

// Commute colour classes, shared by the map (client) and the legend (server).
// Popups show whole minutes, so class edges sit at .5: 20.4 -> "≤ 20", 20.6 -> "21–30".

export const BIN_UPPER_MIN = [20, 30, 45, 60, 90];

export const BINS: [label: string, colour: string][] = [
  ["≤ 20 min", "#1a9850"],
  ["21–30", "#91cf60"],
  ["31–45", "#d9ef8b"],
  ["46–60", "#fee08b"],
  ["61–90", "#fc8d59"],
  ["91–120", "#d73027"],
];
export const OVER_MAX_COLOUR = "#7f0000";
export const NO_DATA_COLOUR = "#999999";
export const NO_RESIDENTS_COLOUR = "#d4d4d4"; // lighter than no data: nobody lives here

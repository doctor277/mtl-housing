// Commute colour classes, shared by the maps and their legends. Labels ("≤ 20 min", "21–30",
// …) come from lib/strings (strings.commute.classLabels). Popups show whole minutes, so class
// edges sit at .5: 20.4 -> "≤ 20", 20.6 -> "21–30".

export const BIN_UPPER_MIN = [20, 30, 45, 60, 90];

/** One colour per class: ≤ 20, 21–30, 31–45, 46–60, 61–90, 91–max_trip_min. */
export const COMMUTE_COLOURS = ["#1a9850", "#91cf60", "#d9ef8b", "#fee08b", "#fc8d59", "#d73027"];
export const OVER_MAX_COLOUR = "#7f0000";
export const NO_DATA_COLOUR = "#999999";
export const NO_RESIDENTS_COLOUR = "#d4d4d4"; // lighter than no data: nobody lives here
/** Results map: neighbourhoods not in the user's results, drawn without data colour. */
export const NOT_IN_RESULTS_COLOUR = "#e2e8f0";

// Every UI string of the site in French (M5.3b), the same shape as en.ts (`Strings`). Québec
// usage (owner's M5 decisions 7–9 and M5.3 answers): "vous"; a non-breaking space (NB) before
// ":" and "%" and inside « »; no space before ";", "?" or "!"; "1 500 $", "≈ 1 475 $",
// "7 h 30", "mardi 1er décembre 2026"; "3½" and "4½" unchanged. Numbers are passed in, never
// typed here. Texts from the data files (campus names, credits, grade words) come in French
// from the pipeline (M5.3a).

import type { Lang } from "../localized";
import type { BedroomType, LabelKey, RentEntry, RentMeta } from "../rent";
import { isLowReliability } from "../rent";
import type { MaxCommute, SearchField, SearchSize } from "../search";
import type { Strings } from "./en";

/** Non-breaking space: before ":" and "%", in numbers, inside « ». */
const NB = " ";

/** "1 500" (a non-breaking space between thousands). */
function dollars(x: number): string {
  return String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g, NB);
}

/** "1 500 $". */
const money = (x: number) => `${dollars(x)}${NB}$`;

/** "≈ 1 475 $": an estimate (rent.json rents are rounded to $25). */
function rentAbout(x: number): string {
  return `≈${NB}${money(x)}`;
}

/** A decimal with a comma: 1.9 -> "1,9"; whole numbers stay whole ("4"). */
const decimal = (x: number) => String(x).replace(".", ",");

/** "15 %". */
const pct = (n: number | string) => `${n}${NB}%`;

/** « … » with non-breaking spaces. */
const quote = (s: string) => `«${NB}${s}${NB}»`;

/** "plus de 2 heures" for the routing limit in minutes (commute.json max_trip_min). */
function overMax(maxMin: number): string {
  if (maxMin % 60 !== 0) return `plus de ${maxMin} min`;
  const h = maxMin / 60;
  return `plus de ${h} ${h === 1 ? "heure" : "heures"}`;
}

/** "a, b ou c". */
function orList(items: string[]): string {
  return items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} ou ${items.at(-1)}`;
}

/** "a, b et c". */
function andList(items: string[]): string {
  return items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} et ${items.at(-1)}`;
}

const wholePct = (share: number) => pct(Math.round(share * 100));
const oneDecimalPct = (share: number) => pct(decimal(Number((share * 100).toFixed(1))));

/** Short campus names for pickers and sentences, the same in both languages. */
const CAMPUS_SHORT: Record<string, string> = {
  udem: "UdeM",
  mcgill: "McGill",
  concordia_sgw: "Concordia SGW",
};

/** A campus name inside a sentence: French says "l’UdeM" (de l’UdeM, vers l’UdeM) but
 * "McGill" and "Concordia" without an article. */
const inText = (campus: string) => (campus === "UdeM" ? "l’UdeM" : campus);

/** Short items joined with " · ", each kept on one line: lines break only between items,
 * never inside "1½–2½" (design review, M5.3b). */
const keepItems = (items: string[]) =>
  items.map((i) => i.replaceAll(" ", NB).replaceAll("–", "–⁠")).join(" · ");

/** A capital at the start of a line: building names are lowercase in running text ("pavillon
 * Roger-Gaudry", owner, M5.3) but open a line with a capital. */
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** "de" before a word, elided before a vowel: "d’octobre 2025", "de novembre 2025". */
const de = (word: string) => (/^[aeiouyéèêh]/i.test(word) ? `d’${word}` : `de ${word}`);

const SIZE_LABELS = { room: "Chambre", studio: "Studio", "1br": "3½", "2br": "4½" } satisfies Record<SearchSize, string>;

const MONTHS = [
  "janvier",
  "février",
  "mars",
  "avril",
  "mai",
  "juin",
  "juillet",
  "août",
  "septembre",
  "octobre",
  "novembre",
  "décembre",
];
const WEEKDAYS = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];

/** "1er décembre 2026" / "20 novembre 2026" from an ISO date or timestamp (date part). */
function dayMonthYear(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  return `${d === 1 ? "1er" : d} ${MONTHS[m - 1]} ${y}`;
}

/** CMHC's period, "October 2025" (rent.json) -> "octobre 2025". */
const EN_MONTHS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
function period(p: string): string {
  const [month, year] = p.split(" ");
  const i = EN_MONTHS.indexOf(month);
  return i < 0 ? p : `${MONTHS[i]} ${year}`;
}

/** StatCan's quarter, "2026 Q2" (rent.json) -> "2e trimestre de 2026". */
function quarter(q: string): string {
  const match = /^(\d{4}) Q([1-4])$/.exec(q);
  if (!match) return q;
  const n = Number(match[2]);
  return `${n === 1 ? "1er" : `${n}e`} trimestre de ${match[1]}`;
}

// --- rent lines --------------------------------------------------------------------------

const BADGES: Record<LabelKey, string> = {
  neighbourhood: "Estimation",
  zone: "Estimation, secteur élargi",
  neighbourhood_low: "Fiabilité faible",
  zone_low: "Fiabilité faible",
  none: "Données insuffisantes",
};

/** CMHC's grade d words, in quotes, as CMHC writes them in French. */
const CAUTION = quote("utiliser avec prudence");

/** Main CMHC line (same rules as en.ts). CMHC areas keep their published names (decision 10). */
function detailLine(e: RentEntry, meta: RentMeta): string {
  const words = meta.grade_words;
  const when = period(meta.cmhc.period);
  const areas = e.cmhc_areas;
  if (e.label === "none") return "La SCHL ne publie pas de loyer fiable pour cette taille ici ni à proximité.";
  const zone = areas[0]?.type === "zone";
  if (areas.length === 1) {
    const name = areas[0].name;
    const word = words[areas[0].grade].fr;
    switch (e.label) {
      case "neighbourhood":
        return `D’après le loyer moyen de la SCHL dans le secteur ${name} (${when}, cote de fiabilité ${quote(word)} de la SCHL).`;
      case "zone":
        return `La SCHL n’a pas de données fiables pour ce secteur; on utilise donc la zone plus large ${name} (cote de fiabilité ${quote(word)} de la SCHL).`;
      case "neighbourhood_low":
        return `D’après le loyer moyen de la SCHL dans le secteur ${name}, que la SCHL qualifie de ${CAUTION}.`;
      case "zone_low":
        return `D’après la zone plus large ${name} de la SCHL, qu’elle qualifie de ${CAUTION}.`;
    }
  }
  const kind = zone ? "les zones de la SCHL" : "les secteurs de la SCHL";
  const names = andList(areas.map((a) => a.name));
  if (isLowReliability(e.label)) {
    return `D’après les loyers moyens de la SCHL dans ${kind} ${names}; la SCHL qualifie au moins l’un d’eux de ${CAUTION}.`;
  }
  return `D’après les loyers moyens de la SCHL dans ${kind} ${names} (${when}).`;
}

/** Extra lines: the split (raw shares, per-area rating) and the coverage. */
function extraLines(e: RentEntry, meta: RentMeta): string[] {
  const words = meta.grade_words;
  const areas = e.cmhc_areas;
  const lines: string[] = [];
  const partial = e.coverage_pct !== null;
  const kind = areas[0]?.type === "zone" ? "des zones de la SCHL" : "des secteurs de la SCHL";
  if (areas.length > 1) {
    const rated = (g: string) => `cote de fiabilité ${quote(words[g].fr)}`;
    const parts = areas.map(
      (a) => `${a.name} (${partial ? oneDecimalPct(a.share) : wholePct(a.share)}, ${rated(a.grade)})`,
    );
    lines.push(`Moyenne pondérée ${kind} ${andList(parts)}, selon le nombre de logements locatifs.`);
  }
  if (partial) {
    const shares = areas.length === 1 ? ` (${areas[0].name}${NB}: ${oneDecimalPct(areas[0].share)})` : "";
    lines.push(
      `Couvre ${pct(e.coverage_pct!)} des logements locatifs de ce quartier${shares}; la SCHL n’a pas de données fiables pour le reste.`,
    );
  }
  return lines;
}

/** Legend text per rent class, in dollars (same rules as en.ts). */
function rentClassRanges(edges: number[], step: number): string[] {
  const out = [`moins de ${money(edges[0])}`];
  for (let i = 0; i < edges.length - 1; i++) out.push(`${money(edges[i])} à ${money(edges[i + 1] - step)}`);
  out.push(`${money(edges[edges.length - 1])} ou plus`);
  return out;
}

/** "< 85 %", "85–95 %", …, "> 130 %". */
function rentClassPct(binPct: number[]): string[] {
  const p = binPct.map((x) => Math.round(x * 100));
  return [`<${NB}${pct(p[0])}`, ...p.slice(1).map((x, i) => pct(`${p[i]}–${x}`)), `>${NB}${pct(p[p.length - 1])}`];
}

// --- commute lines ------------------------------------------------------------------------

/** "≤ 20 min", "21–30", …, "91–120". */
function commuteClassLabels(uppers: number[], maxTripMin: number): string[] {
  const all = [...uppers, maxTripMin];
  return [`≤${NB}${all[0]} min`, ...all.slice(1).map((u, i) => `${all[i] + 1}–${u}`)];
}

export const fr: Strings = {
  lang: "fr" as Lang,
  siteName: "[NAME]",
  contactEmail: "[EMAIL]",
  meta: {
    title: `[NAME]${NB}: où habiter à Montréal sans voiture`,
    description:
      "Choisissez votre campus, la taille du logement, votre budget et votre trajet maximal, et voyez quels quartiers de Montréal vous conviennent.",
    locale: "fr_CA",
    htmlLang: "fr-CA",
  },
  notFound: {
    title: "Page introuvable",
    text: "Cette adresse ne correspond à aucune page du site.",
    home: "Retour à la recherche",
  },
  languageSwitch: { label: "English", lang: "en" },
  format: {
    dollars,
    rent: rentAbout,
    colon: `${NB}: `,
    /** "7 h 30". */
    clock: (minutes: number) => `${Math.floor(minutes / 60)}${NB}h${NB}${String(minutes % 60).padStart(2, "0")}`,
    /** "mardi 1er décembre 2026". */
    longDate: (iso: string) => {
      const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
      return `${WEEKDAYS[new Date(Date.UTC(y, m - 1, d, 12)).getUTCDay()]} ${dayMonthYear(iso)}`;
    },
    /** "20 novembre 2026". */
    date: dayMonthYear,
    andList,
  },
  home: {
    title: "Trouvez où habiter à Montréal sans voiture",
    intro: (count: number) =>
      `Comparez les temps de trajet en transport collectif et les loyers typiques dans ${count} quartiers de Montréal.`,
    submit: "Voir les quartiers",
  },
  form: {
    campus: { legend: "Campus" },
    size: {
      legend: "Taille",
      /** Owner's short form (design review DR5-5, M5.3b). */
      hint: keepItems([
        `Chambre${NB}: dans un appartement partagé`,
        `Studio${NB}: 1½–2½`,
        `3½${NB}: 1 chambre`,
        `4½${NB}: 2 chambres`,
      ]),
      labels: SIZE_LABELS,
    },
    budget: {
      label: "Budget par mois",
      optional: "facultatif",
      hint: (example: string) => `Par exemple ${example}${NB}$. Laissez vide pour trier seulement selon le trajet.`,
      currency: "$",
      currencyFirst: false,
    },
    maxCommute: {
      legend: "Trajet maximal",
      hint: (start: string, end: string) =>
        `Trajet typique en transport collectif jusqu’au campus, marche comprise, en partant entre ${start} et ${end} un matin de semaine.`,
      option: (min: MaxCommute) => `${min} min`,
    },
  },
  results: {
    title: "Quartiers",
    loading: "Chargement…",
    needsJavaScript:
      "Les résultats ont besoin de JavaScript. Activez-le dans votre navigateur pour voir les quartiers.",
    budget: (amount: string) => `jusqu’à ${amount}${NB}$ par mois`,
    noBudget: "sans budget",
    /** Non-breaking spaces: "max." never ends up alone on a line (Impeccable, M5.3b). */
    maxCommute: (min: MaxCommute) => `${min}${NB}min${NB}max.`,
    changeSearch: "Modifier la recherche",
    copyLink: "Copier le lien",
    linkCopied: "Lien copié",
    copyFailed: "Copie impossible. Copiez plutôt l’adresse dans votre navigateur.",
    update: "Mettre à jour",
    sort: { label: "Trier par", commute: "Trajet le plus court", rent: "Loyer le plus bas" },
    view: { label: "Affichage", list: "Liste", map: "Carte" },
    allEstimates: "Tous les loyers sont des estimations.",
    groups: {
      all: "Sélection",
      fits: "Dans votre budget",
      over: "Un peu au-dessus du budget",
      noData: "Données insuffisantes",
    },
    groupHint: {
      over: (p: number) => `Jusqu’à ${pct(p)} au-dessus de votre budget.`,
      noData: `Impossible de comparer ces quartiers à votre budget${NB}: il n’y a pas assez de données de loyer pour cette taille.`,
    },
    showMore: (n: number) => `Afficher ${n} de plus`,
    showFewer: "Afficher moins",
    roomNote: (rent: string) => `Loyer d’une chambre${NB}: ${rent} dans toute la ville, la même estimation partout`,
    roomWarning: (rent: string) =>
      `Le loyer typique d’une chambre (${rent}) dépasse votre budget, et on ne peut pas savoir où les chambres sont moins chères.`,
    hiddenNoCommute: (n: number, campus: string) =>
      n === 1
        ? `1 quartier n’est pas affiché${NB}: il n’y a pas de temps de trajet vers ${inText(campus)} pour ce quartier.`
        : `${n} quartiers ne sont pas affichés${NB}: il n’y a pas de temps de trajet vers ${inText(campus)} pour ces quartiers.`,
    noneWithin: (max: number, campus: string) => `Aucun quartier n’est à moins de ${max} min ${de(inText(campus))}.`,
    tryLonger: "Essayez un trajet maximal plus long.",
    noCommuteData: (campus: string) => `Il n’y a pas de temps de trajet vers ${inText(campus)} pour ces quartiers.`,
    noneFits: (n: number, max: number, p: number) =>
      n === 1
        ? `Le seul quartier à moins de ${max} min dépasse votre budget de plus de ${pct(p)}.`
        : `Les ${n} quartiers à moins de ${max} min dépassent tous votre budget de plus de ${pct(p)}.`,
    cheapest: (name: string, rent: string) => `Le moins cher${NB}: ${name}, ${rent}.`,
    hiddenOverBudget: (n: number, p: number) =>
      n === 1
        ? `1 autre quartier dépasse votre budget de plus de ${pct(p)}.`
        : `${n} autres quartiers dépassent votre budget de plus de ${pct(p)}.`,
    tryBudget: (n: number) =>
      n === 1
        ? "Essayez un budget plus élevé, ou laissez-le vide pour le voir."
        : "Essayez un budget plus élevé, ou laissez-le vide pour tous les voir.",
    invalidTitle: "Cette recherche ne peut pas être utilisée",
    invalid: {
      campus: "Choisissez un des campus.",
      size: `Choisissez une taille${NB}: chambre, studio, 3½ ou 4½.`,
      budget: "Le budget doit être un nombre entier de dollars, ou rester vide.",
      maxCommute: (options: readonly number[]) => `Choisissez un trajet maximal${NB}: ${orList(options.map(String))} min.`,
    } satisfies Record<SearchField, unknown>,
  },
  card: {
    minutes: (min: number) => `${min} min`,
    perMonth: (rent: string) => `${rent} par mois`,
  },
  detail: {
    commuteHeading: "Trajet",
    median: (min: number, target: string, start: string, end: string) =>
      `Environ ${min} min de porte à porte, ${target}, un matin de semaine typique (départ entre ${start} et ${end}).`,
    toClosestBuilding: (campus: string) => `jusqu’au pavillon ${de(inText(campus))} le plus proche`,
    toPlace: (name: string) => `jusqu’au ${name}`,
    range: (lo: number, hi: number | null, maxMin: number) =>
      `Selon l’endroit dans le quartier${NB}:${hi === null ? `de ${lo} min à ${overMax(maxMin)}` : lo === hi ? `${lo} min` : `de ${lo} à ${hi} min`} pour la plupart des logements.`,
    buildings: (parts: { name: string; time: string }[]) =>
      cap(parts.map((p) => `${p.name}${NB}: ${p.time}`).join(" · ")),
    overMax: (maxMin: number) => overMax(maxMin),
    lowSample: (n: number) => `Peu de logements échantillonnés ici (${n}), donc c’est moins certain.`,
    manyUnreachable: (p: number, maxMin: number) =>
      `${pct(p)} des logements de ce quartier sont à ${overMax(maxMin)} en transport collectif.`,
    commuteSource:
      "Les temps de trajet sont calculés à partir des horaires de la STM, du REM et d’exo (CC BY 4.0). Les horaires ne tiennent pas compte des retards ni des pannes.",
    rentHeading: (size: string) => `Loyer, ${size}`,
  },
  rent: {
    badges: BADGES,
    detailLine,
    extraLines,
    sourceLine:
      "Estimation fondée sur les loyers moyens, ajustée aux loyers demandés actuels à Montréal. Ce n’est pas une annonce, et elle peut être sous-estimée là où beaucoup de locataires habitent depuis longtemps.",
    dataLine: (meta: RentMeta) =>
      `Données${NB}: SCHL (${period(meta.cmhc.period)}) et loyers demandés expérimentaux de Statistique Canada (${quarter(meta.statcan.quarter)}).`,
    roomLine: (meta: RentMeta) =>
      `Chambre${NB}: ${rentAbout(meta.room.estimate)} par mois, le loyer demandé moyen d’une chambre dans tout Montréal, pas propre à ce quartier (Statistique Canada, ${quarter(meta.statcan.quarter)}).`,
    classRanges: rentClassRanges,
    classPct: rentClassPct,
    sizeLabel: (size: Exclude<BedroomType, "3br_plus">) => SIZE_LABELS[size],
  },
  commute: {
    campusShort: (id: string, fullName: string) => CAMPUS_SHORT[id] ?? fullName,
    classLabels: commuteClassLabels,
  },
  share: {
    /** "UdeM · 3½ · ≤ 1 500 $/mois · 45 min" (the site name comes from og:site_name). */
    title: (campus: string, size: string, budget: string | null, maxCommute: number) =>
      [campus, size, ...(budget ? [`≤${NB}${budget}${NB}$/mois`] : []), `${maxCommute} min`].join(" · "),
    description: (campus: string, sizeInSentence: string, maxCommute: number, budget: string | null) =>
      `Les quartiers de Montréal à moins de ${maxCommute} min ${de(inText(campus))} en transport collectif, pour ${sizeInSentence}${budget ? ` jusqu’à ${budget}${NB}$ par mois` : ""}, avec des loyers estimés.`,
    sizeInSentence: {
      room: "une chambre",
      studio: "un studio",
      "1br": "un 3½",
      "2br": "un 4½",
    } satisfies Record<SearchSize, string>,
  },
  example: {
    lead: `Vous hésitez? Essayez un exemple${NB}:`,
    label: (campus: string, size: string, budget: number, maxCommute: number) =>
      `${campus}, ${size}, ${money(budget)}, ${maxCommute} min`,
  },
  footer: {
    dataLine: (scheduleDay: string, cmhcPeriod: string, statcanQuarter: string) =>
      `Données${NB}: horaires de la STM, du REM et d’exo du ${scheduleDay}; loyers de la SCHL (${period(cmhcPeriod)}) et loyers demandés expérimentaux de Statistique Canada (${quarter(statcanQuarter)}). Des estimations, pas des annonces.`,
    navLabel: "À propos de ce site",
    howItWorks: "Comment ça marche",
    sources: "Sources",
  },
  howItWorks: {
    title: "Comment ça marche",
    lead: "D’où viennent les temps de trajet et les loyers, et comment la sélection est faite.",
    commute: {
      heading: "Temps de trajet",
      doorToDoor: `Les temps sont de porte à porte en transport collectif, marche comprise${NB}: des logements de chaque quartier jusqu’à l’entrée du campus.`,
      schedule: (start: string, end: string, day: string) =>
        `Chaque trajet partant entre ${start} et ${end} est planifié avec les horaires de la STM, du REM et d’exo du ${day}, un jour de semaine au nombre de passages typique. Le temps de chaque logement est la médiane de ces trajets, donc il comprend une attente typique; le temps du quartier est la médiane de ses logements.`,
      range: `${quote("Pour la plupart des logements")} désigne l’intervalle entre le 10e et le 90e centile des logements du quartier, pondérés selon le nombre de ménages.`,
      walking: (kmh: number) =>
        `La marche est comptée à ${decimal(kmh)} km/h, comme les temps de marche de Google Maps.`,
      closest: (campus: string, buildings: string) =>
        `Pour ${inText(campus)}, le temps de chaque logement est celui du pavillon atteint en premier${NB}: ${buildings}. Un cours dans un autre pavillon peut ajouter quelques minutes.`,
      adjustmentsLead: `Les temps vers ces pavillons comprennent une petite correction fixe pour la marche entre le quai du métro et l’entrée du pavillon, que le planificateur de trajets calcule mal. Elle a été fixée en comparant avec Google Maps${NB}:`,
      adjustment: (building: string, signed: string) => `${cap(building)}${NB}: ${signed}`,
      limits: "Les horaires ne tiennent pas compte des retards, des détours ni des pannes.",
    },
    rent: {
      heading: "Loyers",
      method: (cmhcPeriod: string, statcanQuarter: string) =>
        `Le loyer de chaque quartier est le loyer moyen de la SCHL dans ce quartier (${period(cmhcPeriod)}) divisé par la moyenne de la SCHL pour Montréal, multiplié par le loyer demandé actuel à Montréal selon Statistique Canada (${quarter(statcanQuarter)}).`,
      oldLeases:
        "Les moyennes de la SCHL comprennent les locataires de longue date, qui paient généralement moins qu’un nouveau locataire. Dans les quartiers aux immeubles plus anciens, les loyers peuvent sembler plus bas que ceux des annonces.",
      rounding: (step: number) => `Les loyers sont arrondis aux ${step}${NB}$ près et affichés avec ≈.`,
      labelsLead: `Quand la donnée de la SCHL pour un quartier manque ou est moins fiable, le loyer l’indique${NB}:`,
      labels: {
        zone: "utilise la donnée de la SCHL pour le secteur environnant, plus large.",
        low: `la SCHL qualifie sa donnée de ${CAUTION}.`,
        none: "la SCHL ne publie aucune donnée fiable ici ni à proximité, donc il n’y a pas d’estimation.",
      },
    },
    shortlist: {
      heading: "La sélection",
      maxCommute: "Seuls les quartiers à l’intérieur de votre trajet maximal sont affichés.",
      budget: (p: number) =>
        `Avec un budget, ils sont regroupés${NB}: dans votre budget, un peu au-dessus (jusqu’à ${pct(p)} de plus) et données insuffisantes. Les quartiers à plus de ${pct(p)} au-dessus sont exclus, et la page indique combien. Le loyer comparé est le loyer arrondi que vous voyez.`,
      noBudget: "Sans budget, ils sont classés selon le trajet.",
      rooms: `Les chambres ont une seule donnée pour toute la ville${NB}: elles sont donc classées selon le trajet et le budget ne les filtre pas.`,
    },
    sources: {
      text: `Chaque source avec sa licence et sa date, la vérification des temps de trajet et les limites connues${NB}:`,
      link: "Sources et limites",
    },
  },
  sources: {
    title: "Sources et limites",
    lead: "D’où vient chaque chiffre de ce site, à quel point il est fiable, et ce qu’il ne peut pas vous dire.",
    limits: {
      heading: "Limites connues",
      oldLeases: {
        heading: "Les loyers des quartiers plus anciens peuvent sembler bas",
        text: "Les loyers moyens de la SCHL comprennent les locataires de longue date, qui paient généralement moins qu’une personne qui signe un bail aujourd’hui. Les quartiers où les immeubles anciens sont nombreux, comme le Plateau-Mont-Royal ou Rosemont, paraissent donc probablement moins chers que leurs annonces, et les secteurs aux immeubles plus récents, comme l’Ouest-de-l’Île, probablement plus chers. L’ajustement aux loyers demandés actuels de Statistique Canada corrige le niveau de l’ensemble de la ville, pas cet écart. Son ampleur dans chaque quartier n’a pas encore été mesurée.",
      },
      concordiaEast: {
        heading: `Concordia${NB}: trajets arrivant de l’est`,
        text: (walk: number) =>
          `Pour les trajets qui arrivent par la ligne verte depuis l’est, les exemples d’itinéraires du planificateur descendent à Peel et marchent ${walk} minutes, au lieu de rouler un arrêt de plus jusqu’à Guy-Concordia. Pour l’un de ces trajets, vérifié en entier, le temps affiché ici est plus court que tous les itinéraires que propose le planificateur${NB}: les temps passent donc très probablement par Guy-Concordia. On ignore pourquoi les deux diffèrent.`,
      },
      firstWait: {
        heading: "L’attente du premier train ou autobus",
        text: (ours: number, google: number, start: string, end: string) =>
          `De la gare REM Fairview–Pointe-Claire à McGill, le temps affiché ici est de ${ours} min et Google Maps donne ${google} min, pour le même trajet en REM. L’écart vient très probablement de l’attente du train${NB}: le temps affiché ici est la médiane des départs entre ${start} et ${end}, donc il comprend une attente typique, alors que le trajet de Google part au bon moment. Si vous choisissez l’heure de votre départ, un trajet qui commence par un train ou un autobus peu fréquent peut être plus court qu’affiché.`,
      },
    },
    validation: {
      heading: "Comment les temps de trajet ont été vérifiés",
      method: (day: string, rulePct: number, ruleMin: number) =>
        `Les temps de trajet ont été comparés à ceux de Google Maps, ${quote(`arriver à 8${NB}h${NB}30`)} le ${day}, sur des trajets d’essai vers chaque campus. Un trajet est réussi quand l’écart est d’au plus ${ruleMin} minutes ou ${pct(rulePct)}, la plus grande des deux valeurs.`,
      campus: (campus: string, pass: number, total: number) =>
        `${campus}${NB}: ${pass} comparaisons réussies sur ${total}.`,
      udemBuildings: "Un trajet vers l’UdeM est comparé avec ses deux pavillons, donc il compte deux fois.",
      udemRoute4: (first: number, likeForLike: number, ours: number) =>
        `La comparaison échouée de l’UdeM, depuis Hochelaga${NB}: la première suggestion de Google est un autre trajet, plus lent (${first} min). Par rapport au trajet de ${likeForLike} minutes de Google par la ligne verte et le REM, le temps affiché ici (${ours} min) est réussi.`,
      udemRoute3: (first: number, fastest: number, ours: number) =>
        `C’est l’inverse depuis Sault-au-Récollet${NB}: le temps affiché ici (${ours} min) est réussi par rapport à la première suggestion de Google (${first} min), mais pas par rapport au trajet le plus rapide qu’elle propose (${fastest} min), une correspondance d’autobus bien synchronisée.`,
      mcgillRoute5: `La comparaison échouée de McGill est celle décrite sous ${quote("L’attente du premier train ou autobus")}, plus haut.`,
      inSample:
        "La vitesse de marche a été ajustée sur les trajets vers l’UdeM; les résultats de l’UdeM montrent donc un ajustement, pas un test indépendant. La correction de marche de chaque pavillon a été fixée sur sa propre marche depuis le quai du métro (les deux pavillons de l’UdeM et celui de Concordia). Les trajets vers McGill et Concordia partent des mêmes endroits que ceux de l’UdeM et ont été vérifiés ensuite, sans changer la vitesse de marche. Avant le lancement, quelques nouveaux trajets seront vérifiés avec les réglages figés, et le résultat sera publié, réussi ou non.",
      cite: (file: string, udemDate: string, othersDate: string) =>
        `Temps de Google Maps relevés le ${udemDate} (UdeM) et le ${othersDate} (McGill, Concordia). Résultats complets${NB}: ${file}, dans le code du projet.`,
    },
    commute: {
      heading: `Temps de trajet${NB}: limites`,
      oneMorning: (start: string, end: string, day: string) =>
        `Un seul matin de semaine${NB}: les trajets partant entre ${start} et ${end} le ${day}. Les soirs, les fins de semaine et les horaires ultérieurs peuvent différer.`,
      delays: `Des horaires, pas le service réel${NB}: les retards, les détours et les pannes ne sont pas pris en compte.`,
      flatWalking: (kmh: number) =>
        `La marche est comptée à ${decimal(kmh)} km/h sur terrain plat${NB}: les côtes et les escaliers ne sont pas modélisés. Les corrections fixes de certains pavillons, indiquées dans Comment ça marche, couvrent la marche du quai du métro jusqu’à la porte, y compris la montée vers le pavillon Roger-Gaudry de l’UdeM.`,
      transfers: "Une correspondance est comptée comme une marche entre les deux arrêts. Les longs corridors de station peuvent prendre plus de temps.",
      buildings:
        "Chaque campus correspond à un ou deux pavillons. Un cours dans un autre pavillon peut changer le trajet de 5 à 10 minutes. Le campus Macdonald de McGill et le campus Loyola de Concordia ne sont pas couverts.",
      census:
        "Les logements sont placés aux points des petites zones du Recensement de 2021 (aires de diffusion) et pondérés selon leurs ménages de 2021; les secteurs construits depuis, surtout au centre-ville, comptent donc un peu moins qu’ils le devraient.",
      maxTrip: (max: number) =>
        `Les trajets sont cherchés jusqu’à ${max} minutes. Un logement sans trajet dans cette limite est compté à ${overMax(max)}.`,
      outOfScopeLead: `Exclus des temps de trajet${NB}:`,
    },
    rent: {
      heading: `Loyers${NB}: limites`,
      method: (cmhcPeriod: string, statcanQuarter: string) =>
        `Les loyers sont des estimations, pas des annonces${NB}: les écarts entre quartiers viennent de la SCHL (${period(cmhcPeriod)}), et le niveau actuel du loyer demandé à Montréal, de Statistique Canada (${quarter(statcanQuarter)}). On suppose que les écarts ${de(period(cmhcPeriod))} tiennent toujours.`,
      experimental: "Les loyers demandés de Statistique Canada sont des estimations expérimentales.",
      coverage: `La SCHL couvre les immeubles construits pour la location comptant au moins 3 logements${NB}: pas les condos loués par leurs propriétaires, ni les chambres.`,
      rooms: (amount: string, q: string) =>
        `Les chambres ont une seule donnée pour tout Montréal, ${amount} par mois (Statistique Canada, ${quarter(q)}); on ne peut donc pas les comparer d’un quartier à l’autre.`,
      crosswalkLead: `Les secteurs de la SCHL ne suivent pas les quartiers de la Ville; chaque quartier est donc associé aux secteurs de la SCHL au moyen des secteurs de recensement. Notes sur cette association${NB}:`,
      crosswalkNote: (neighbourhood: string | undefined, text: string) =>
        neighbourhood ? `${neighbourhood}${NB}: ${text}` : text,
    },
    list: {
      heading: "Sources",
      lead: "Toutes les données sont gratuites et ouvertes. Aucun site d’annonces n’est utilisé.",
      commuteHeading: "Temps de trajet",
      rentHeading: "Loyers",
      licence: {
        ccBy4: "CC BY 4.0",
        odbl: "ODbL 1.0",
        statcanOpen: "Licence ouverte de Statistique Canada",
        cmhcData: "Entente de licence avec la SCHL pour l’utilisation de données",
      },
      licenceLabel: `Licence${NB}:`,
      items: {
        stm: {
          name: "Horaires de la STM (autobus et métro)",
          publisher: "Société de transport de Montréal",
          note: "Les horaires du métro de la STM sont indicatifs. Ils servent seulement à calculer les temps de trajet; aucun horaire n’est affiché.",
        },
        rem: {
          name: "Horaires du REM (fichier GTFS, téléchargement)",
          publisher: "Réseau express métropolitain",
          publisherUrl: "https://rem.info/fr",
          note: "Le REM publie ses horaires seulement sous la forme de ce fichier.",
        },
        exo: { name: "Horaires d’exo (trains de banlieue)", publisher: "exo" },
        osm: { name: "Rues et sentiers pour la marche", publisher: "Contributeurs d’OpenStreetMap, par Geofabrik" },
        quartiers: { name: "Limites des quartiers (quartiers de référence en habitation)", publisher: "Ville de Montréal" },
        census: {
          name: `Où habitent les gens${NB}: Fichier des attributs géographiques, Recensement de 2021 (92-151-X)`,
          publisher: "Statistique Canada",
        },
        cmhc: {
          name: `Enquête sur les logements locatifs${NB}: loyers moyens et nombre de logements locatifs par secteur`,
          publisher: "SCHL",
        },
        statcanRent: {
          name: "Loyers demandés, tableau 46-10-0092-01 (estimations expérimentales)",
          publisher: "Statistique Canada",
        },
      },
      dates: {
        feed: (start: string, end: string) => `Horaires valides du ${start} au ${end}.`,
        osm: (date: string) => `Données au ${date}.`,
        downloaded: (date: string) => `Téléchargé le ${date}.`,
        census: "Recensement de 2021.",
        cmhc: (p: string) => `Enquête ${de(period(p))}.`,
        statcanRent: (q: string, released: string) => `${quarter(q)}, publié le ${released}.`,
      },
      creditsLead: `Mentions de source, comme les éditeurs les demandent${NB}:`,
    },
    about: {
      heading: "À propos",
      notAffiliated:
        "Ce site n’est affilié ni à l’UdeM, ni à McGill, ni à Concordia, ni à la STM, ni au REM, ni à exo, ni à la SCHL, ni à Statistique Canada.",
      contact: (email: string) => `Questions ou corrections${NB}: ${email}`,
    },
  },
  resultsMap: {
    colourBy: "Couleurs selon",
    hint: "Touchez un quartier pour voir son trajet et son loyer. La liste donne les mêmes renseignements.",
    commuteLegend: (campus: string) => `Trajet typique vers ${inText(campus)}`,
    rentLegend: (size: string) => `Loyer d’un ${size.toLowerCase()}, comparé au loyer demandé à Montréal`,
    inResults: `Dans vos résultats${NB}: contour foncé`,
    pin: `Épingle${NB}: le pavillon du campus vers lequel les temps sont mesurés`,
    notInResults: "Hors de vos résultats",
    showDetails: "Voir les détails",
    numbers: (minutes: string, rent: string | null) => (rent ? `${minutes} · ${rent}` : minutes),
    out: {
      tooFar: (max: number, campus: string) =>
        `Hors de vos résultats${NB}: à plus de ${max} min ${de(inText(campus))}.`,
      overBudget: (p: number) => `Hors de vos résultats${NB}: plus de ${pct(p)} au-dessus de votre budget.`,
      noCommute: (campus: string) => `Hors de vos résultats${NB}: pas de temps de trajet vers ${inText(campus)}.`,
      unknown: "Hors de vos résultats.",
    },
    noResidents: "Aucun résident (parc)",
  },
  map: {
    modes: { commute: "Trajet", rent: "Loyer" },
    loadingMap: "Chargement de la carte…",
    rentClass: (p: string, range: string) => `${p}${NB}: ${range}`,
    lowReliability: `fiabilité faible (SCHL${NB}: ${CAUTION})`,
    notEnoughData: "données insuffisantes",
    attribution: (withRent: boolean) =>
      `Quartiers${NB}: Ville de Montréal (CC BY 4.0). Horaires${NB}: STM, REM, exo (CC BY 4.0). ${withRent ? `Loyers${NB}: SCHL, Statistique Canada. ` : ""}Données cartographiques © les contributeurs d’OpenStreetMap.`,
    error: (message: string) => `La carte n’a pas pu se charger${NB}: ${message}`,
    marker: (campusName: string, destination: string) => `${campusName}${NB}: ${destination}`,
    popup: {
      signedMin: (adj: number) => `${adj > 0 ? "+" : "−"}${decimal(Math.abs(adj))} min`,
      noResidents: (mode: "commute" | "rent") =>
        `Aucun résident, donc aucun ${mode === "rent" ? "loyer estimé" : "temps de trajet"} n’est affiché.`,
      partOf: (parent: string) => `Dans les données de la Ville, ce secteur fait partie du quartier ${parent}.`,
    },
  },
};

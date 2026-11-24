# Product

<!-- impeccable:product-schema 1 -->

Written for the Impeccable design tool in M4.1, from the owner's brief: README.md,
docs/ROADMAP.md ("M4" row and "M4 decisions"), docs/methodology.md, DATA_SOURCES.md, and
reviewed by the owner in the M4.1 PR.

## Platform

web

## Users

University students (UdeM, McGill, Concordia SGW) and other renters without a car, choosing
where in Montréal to look for an apartment. Often on a phone, often new to Montréal or to
Québec apartment names (3½, 4½), often before the 1 July moving season or in August before
the fall term.

## Product Purpose

Answer "where should I live without a car?": the user gives a campus, an apartment size, an
optional budget and a longest acceptable commute, and gets a shortlist of neighbourhoods
with a transit commute and an estimated rent, each with its source and reliability.

## Positioning

Real transit routing (R5 on the STM, REM and exo schedules, checked against Google) and rent
estimates from public statistics (CMHC, Statistics Canada), with "not enough data" shown
instead of guesses. Not a listings site: it says where to look, not what to rent.

## Operating Context

One short search, then reading results. Results are shortlist cards first; the map is a
second view the user switches to, never the first screen (owner, M4).

## Capabilities and Constraints

- Sizes: Room, Studio, 3½, 4½. Room rent is one citywide figure, the same everywhere.
- Budget is optional; with none, results are sorted by commute without budget groups.
- Max commute: 20 / 30 / 45 / 60 min buttons, a hard filter.
- No accounts, no sign-up, no analytics. English and French at launch (French in M5); every
  UI string lives in `lib/strings/`.
- The site name is a placeholder (`[NAME]`) until M6.

## Brand Commitments

None yet beyond honesty: every number comes from a cited source; when data is too thin the
site says "not enough data" (CLAUDE.md, "Never fake data").

## Evidence on Hand

`web/public/data/commute.json`, `rent.json`, `neighbourhoods.geojson` (pipeline outputs).
No testimonials, user counts or press: none may be invented.

## Product Principles

1. Honest over impressive: a number is shown with its source and reliability, or not at all.
2. The search answers the question; the map explains it.
3. Plain words a newcomer understands (explain 3½ and 4½).

## Accessibility & Inclusion

WCAG 2.2 AA (owner's default for M4). Usable on a phone with one thumb; works without
JavaScript for the search form.

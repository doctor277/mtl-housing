---
name: design-review
description: Designer's eye audit of this repo's web app, run ONCE at the end of M4 - first impression, inferred design system, page-by-page checklist, flows, grades. Report only - findings go to the owner in the PR and are not applied without asking. Adapted from gstack's /design-review (MIT) to use the Playwright MCP tools.
---

# /design-review: audit and report (mtl-housing)

Adapted from gstack's `/design-review` (github.com/garrytan/gstack, commit `aab606e`, MIT,
© 2026 Garry Tan; licence in `.claude/skills/LICENSE-gstack.txt`). What was kept: the
designer's audit method, checklist, grading and critique format. What was removed:
gstack's preamble, config, telemetry, "learnings", its Aside/`$B` browser, mockup
generation, its detector scans and **its fix loop**.

**Owner's rules (they win):**
- Run **once, at the end of M4**.
- **Report only.** List the findings in the PR for the owner. **Don't apply any of them
  without asking.**
- **Impeccable wins** any design conflict. Where a finding contradicts the committed
  design system (`web/design/`, with Impeccable's overrides in `web/DESIGN.md`) or an Impeccable decision, say so and mark it "conflicts
  with Impeccable/design system": the owner decides.

## Setup

1. Build and serve: `npm --prefix web run build`, then
   `npm --prefix web run start -- --port 3100` in the background. Stop it at the end.
2. Browser: the Playwright MCP tools (`browser_resize`, `browser_navigate`,
   `browser_snapshot`, `browser_take_screenshot`, `browser_click`, `browser_evaluate`,
   `browser_console_messages`). Read every screenshot you save so the owner can see it.
3. Report dir: `data/interim/design-review/run-<YYYYMMDDTHHMMSSZ>/` with `screenshots/`.
4. Scope: every page of the site (first screen, results, detail, map view, how it works).
   Viewports: phone 390 × 844, tablet 768 × 1024, desktop 1440 × 900.
5. **Never read source code** to judge the design. Judge the rendered page.

## Phase 1: First impression (first screen, desktop and phone)

Full-page screenshot, then write:
- "The site communicates **[what]**."
- "I notice **[observation]**."
- "The first 3 things my eye goes to are: **[1]**, **[2]**, **[3]**." Are they the
  intended three? If not, the hierarchy is lying.
- "In one word: **[word]**."
- **Page area test:** name each area's purpose. Any area you can't name in 2 seconds is
  poorly defined.

## Phase 2: Inferred design system (what is rendered, not what the docs say)

With `browser_evaluate`: font families in use, colours (text and background), the heading
scale (h1–h6 size and weight), and touch targets under 44 px. Flag more than 3 font
families, more than 12 non-grey colours, skipped heading levels, non-scale spacing. Compare
with `web/DESIGN.md` (the system in use). Differences are findings.

## Phase 3: Page by page

For each page: snapshot, screenshot at the three viewports, console errors. Run the **trunk
test**: with no context, can you tell (1) what site this is, (2) what page, (3) the main
sections, (4) your options, (5) where you are, (6) how to search? 4–5 = partial, 3 or fewer
= a high-impact finding.

Checklist (rate each finding high / medium / polish):
1. **Hierarchy:** one focal point and one primary action per view; purpose clear in 3 s;
   squint test; intentional white space.
2. **Typography:** ≤ 3 families; consistent scale; body ≥ 16 px, labels ≥ 12 px; line height
   ~1.5 body; 45–75 characters per line; no skipped heading levels; curly quotes; `…` not
   `...`; tabular numbers for rents and minutes.
3. **Colour and contrast:** WCAG AA (body 4.5:1, large text and UI parts 3:1); no colour-only
   meaning (the rent classes and commute classes have labels); no red/green-only pairs;
   consistent neutrals.
4. **Spacing and layout:** a spacing scale; consistent alignment; max content width; nothing
   floating off the grid; no horizontal scroll; safe-area insets on phones.
5. **Interaction states:** hover, visible focus, pressed, disabled; loading, empty and error
   states designed ("not enough data", no results, hidden-by-commute line); touch targets
   ≥ 44 px; every choice obvious.
6. **Responsive:** the phone layout makes design sense, not just stacked desktop columns;
   forms usable on a phone; correct input types.
7. **Motion:** purposeful, 50–700 ms, ease-out; `prefers-reduced-motion` respected; no
   `transition: all`.
8. **Content and microcopy:** specific button labels; no placeholder text; truncation
   handled; active voice; instructions longer than one sentence mean the design failed;
   flag happy talk ("Welcome to…").
9. **AI slop:** purple gradients, the 3-column icon feature grid, centred everything,
   uniform bubbly radius, decorative blobs, emoji as design, coloured left borders on cards,
   generic hero copy, cards as the container for everything, stats rows of big numbers,
   "Get started / Learn more" as the only actions, only the happy path designed.
10. **Performance as design:** no visible layout shift; fast first content; no font flash.

**Mode:** this site is an **app (Operate)**. Calm surfaces, strong type, few colours, dense
but readable, cards only when the card is the interaction, utility copy (orientation,
status, action).

## Phase 4: Flows

Walk 2–3 flows (search → shortlist → detail → map; change budget; change size to room).
Judge response feel, feedback clarity, form polish. Keep a goodwill meter that starts at 70:
- drains: hidden information −15, forced steps −15, format punishment −10, unnecessary
  questions −10, sloppy look −10, each ambiguous choice −5;
- fills: top task obvious +10, graceful error recovery +10, upfront about limits +5, each
  saved step +5.

Below 30 = critical, 30–60 = needs work, above 60 = healthy.

## Phase 5: Cross-page consistency

Same header/footer, same components styled the same, one tone, same spacing rhythm.

## Phase 6: Report (`design-review.md` in the run dir; findings in the PR)

- **Grades:** each category starts at A; each high finding drops one letter, each medium
  half a letter; polish findings don't change the grade. Design score = weighted average:
  hierarchy 15, typography 15, spacing 15, colour 10, interaction 10, responsive 10,
  content 10, AI slop 5, motion 5, performance 5. Give the AI-slop grade separately too.
- **Findings** (5–10 well-evidenced beat 20 vague ones). Each: id, impact, category, page,
  screenshot, and a critique as "I notice… / I wonder… / What if… / I think… because…" with a
  specific change ("change X to Y because Z").
- **Quick wins:** the 3–5 highest-impact fixes that take under 30 minutes.
- **Conflicts:** findings that contradict the design system or Impeccable, marked as such.
- End with: "None of these were applied. Tell me which ones to do."

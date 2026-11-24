# Design

The design system in use. Two sources, with fixed roles (CLAUDE.md, "Plugins"):

1. **UI UX Pro Max generated the base system once** (M4.1, 2026-11-23):
   [`design/MASTER.md`](design/MASTER.md), [`design/tokens.css`](design/tokens.css),
   [`design/tokens.json`](design/tokens.json), [`design/preview.html`](design/preview.html).
   Query: "housing search tool students transit mobile", dials variance 4, motion 3,
   density 5. Those files are kept exactly as generated and are not regenerated.
2. **Impeccable critiques it and wins any conflict.** Its overrides are below. Where this
   file and `MASTER.md` disagree, this file is what the code does.

The tokens themselves live in [`app/globals.css`](app/globals.css) (`@theme`).

## Scene

A student filling in a short search on a phone, on campus or on the bus, by day or in the
evening; then reading a shortlist. Light only: daytime use, and the map's data colours
(rent and commute classes) were validated on a light basemap. No dark mode.

## Kept from MASTER.md

- **Palette roles:** background `#f8fafc` (paper), card `#ffffff` (surface), foreground
  `#0f172a` (ink), muted foreground `#475569`, ring `#2563eb`.
- **Body face:** Public Sans (self-hosted by `next/font`).
- **Spacing scale:** 4 / 8 / 16 / 24 / 32 / 48 / 64 px (Tailwind's 1, 2, 4, 6, 8, 12, 16).
- **Control radius:** 8 px. **Touch targets:** at least 44 px (choices and buttons are 48).
- **Style:** flat, no gradients; visible focus; 150–200 ms colour transitions; no emoji as
  icons; no colour-only meaning.

## Overridden by Impeccable, and why

| MASTER.md says | Used instead | Why |
|---|---|---|
| Heading font Lexend Mega ("bold, neubrutalist, loud, quirky") | Public Sans for everything | An app people operate needs one calm workhorse family; a very wide display face fights long French words (M5) and contradicts MASTER's own "flat, minimal" style. |
| Accent / CTA orange `#EA580C` with black text | Primary action in ink `#0f172a`, white text | Orange already means "pricier than average" on the rent map. Colour is kept for data: the UI is ink on paper, blue only for links and focus. |
| Primary blue `#2563EB` for buttons | Blue only for focus ring (`#2563eb`) and links (`#1d4ed8`, 6.4:1) | Same reason: the rent map's "cheaper" classes are blue. |
| Border `#E4ECFC` on inputs | Control edges `#64748b` (4.6:1 on paper); `#e2e8f0` only for dividers | WCAG 1.4.11: a control's edge needs 3:1. MASTER's border is 1.2:1. |
| Destructive `#DC2626` | Error text `#b91c1c` (6.2:1) | More margin above AA for small error text. |
| Input focus: `outline: none` + 20% box-shadow | 2 px solid outline, 2 px offset, `#2563eb` | A faint glow is not a visible focus indicator. |
| Shadows sm–xl; cards with shadow, hover lift (`translateY`), `transition: all` | No shadows; borders and spacing separate things; colour-only transitions | MASTER's own style is flat; lifts and `transition: all` are motion without meaning. |
| Page pattern "Product demo + features" (hero video, feature sections) | The first screen is the tool: one line, then the search | Owner's first-screen spec; this is an app, not a landing page. |
| GSAP scroll reveal | No scroll animation, no GSAP | Content is visible by default; an extra library for decoration isn't justified. |
| Modal spec (blur backdrop) | No modals | Nothing here needs to interrupt. |

## Components so far (M4.1, M4.2)

- **Choice:** a fieldset of native radio buttons drawn as 48 px buttons in a grid; unselected
  = white with control edge, selected = ink fill, white semibold text; pressed = the hover
  colour (touch has no hover). On the first screen nothing is preselected: every choice is
  the user's ("Change search" on the results starts from the current search). Works with
  keyboard (arrow keys), screen readers and without JavaScript.
- **Budget field:** labelled number input with a `$` prefix, `step` 25.
- **Primary button:** ink, 48 px, full width on phones, content width from `sm`.
- **Text links:** `#1d4ed8`, underlined, semibold; standalone ones have a 44 px hit area.
- **Shortlist card:** a native `<details>` in a white card with a control edge. Summary: name
  and borough on the left; minutes (semibold) and rent, tabular, on a shared right edge; a
  caveat badge, if any, on its own line. Opening it shows the detail panel in place (no modal).
- **Reliability badge:** words, never colour, and only for real caveats: "Wider-area
  estimate" has a solid outline; "Low reliability" and "Not enough data" a dashed one. The
  normal case is said once above the list ("All rents are estimates.", ROADMAP decision 16).
- **Sort toggle:** two links styled like Choice buttons (ink = current, `aria-current`), so it
  works without JavaScript.
- **Show more:** a `<details>` per group after the first 5 cards; its control stays in place and
  reads "Show fewer" when open.
- **Browser surfaces:** themed selection, caret, accent colour and focus ring; no browser tap
  tint. Tabular numerals only where numbers line up in columns (minutes and rents on cards).

The map (`/map`) keeps its own M2.6/M3 styling until M4.3 reworks it as the results' second
view.

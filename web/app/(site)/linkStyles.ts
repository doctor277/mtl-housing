// A standalone text link that sits in running text or a list: a 44 px hit area (web/DESIGN.md,
// "Text links") from an invisible ::after 9 px above and below the 26 px line. The line keeps
// its height, one-line and two-line links space alike, and the focus ring stays around the
// text (QA M5.2).
export const hitAreaLink =
  "relative inline-block font-semibold text-link underline after:absolute after:inset-x-0 after:-inset-y-[9px] after:content-['']";

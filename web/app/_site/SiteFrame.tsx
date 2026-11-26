// The frame of every page, in one language (M5.3b): <html lang>, the header with the site name
// and the switch to the other language, and the footer with the honest data line (dates from
// the data files) and links. French and English each have their own root layout
// (app/(fr)/layout.tsx, app/(en)/layout.tsx) that renders this with its language.
import { Public_Sans } from "next/font/google";
import Link from "next/link";
import { loadCommute, loadRent } from "@/lib/data";
import type { Lang } from "@/lib/localized";
import { PATHS } from "@/lib/routes";
import { getStrings } from "@/lib/strings";
import LanguageSwitch from "./LanguageSwitch";
import "../globals.css";

// One family for the whole UI (web/DESIGN.md): Public Sans, self-hosted by next/font at build.
const publicSans = Public_Sans({
  variable: "--font-public-sans",
  subsets: ["latin"],
});

const footerLink = "inline-flex min-h-11 items-center font-semibold text-link underline";

export default async function SiteFrame({ lang, children }: { lang: Lang; children: React.ReactNode }) {
  const s = getStrings(lang);
  const paths = PATHS[lang];
  const [commute, rent] = await Promise.all([loadCommute(), loadRent()]);
  const day = s.format.longDate(commute.meta.analysis_date);
  return (
    <html lang={s.meta.htmlLang} className={`${publicSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <header className="border-b border-line">
          <div className="mx-auto flex h-14 w-full max-w-2xl items-center justify-between gap-4 px-4">
            <Link href={paths.home} className="-mx-2 flex min-h-11 items-center px-2 font-semibold tracking-tight no-underline">
              {s.siteName}
            </Link>
            <LanguageSwitch lang={lang} label={s.languageSwitch.label} toLang={s.languageSwitch.lang} />
          </div>
        </header>
        <main className="mx-auto w-full max-w-2xl flex-1 px-4 pt-8 pb-16 sm:pt-12">{children}</main>
        <footer className="border-t border-line">
          <div className="mx-auto w-full max-w-2xl px-4 pt-6 pb-10 text-sm">
            <p className="max-w-prose text-ink-muted">
              {s.footer.dataLine(day, rent.meta.cmhc.period, rent.meta.statcan.quarter)}
            </p>
            <nav aria-label={s.footer.navLabel} className="mt-2 flex flex-wrap gap-x-6">
              <Link href={paths.howItWorks} className={footerLink}>
                {s.footer.howItWorks}
              </Link>
              <Link href={paths.sources} className={footerLink}>
                {s.footer.sources}
              </Link>
            </nav>
          </div>
        </footer>
      </body>
    </html>
  );
}

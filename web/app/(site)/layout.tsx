// Shared frame of the site's pages (form, results, how it works): header, and a footer with
// the honest data line (dates from the data files) and links.
import Link from "next/link";
import { loadCommute, loadRent } from "@/lib/data";
import { strings } from "@/lib/strings";

const footerLink = "inline-flex min-h-11 items-center font-semibold text-link underline";

export default async function SiteLayout({ children }: LayoutProps<"/">) {
  const [commute, rent] = await Promise.all([loadCommute(), loadRent()]);
  const day = strings.format.longDate(commute.meta.analysis_date);
  return (
    <>
      <header className="border-b border-line">
        <div className="mx-auto flex h-14 w-full max-w-2xl items-center px-4">
          <Link href="/" className="-mx-2 flex min-h-11 items-center px-2 font-semibold tracking-tight no-underline">
            {strings.siteName}
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 pt-8 pb-16 sm:pt-12">{children}</main>
      <footer className="border-t border-line">
        <div className="mx-auto w-full max-w-2xl px-4 pt-6 pb-10 text-sm">
          <p className="max-w-prose text-ink-muted">
            {strings.footer.dataLine(day, rent.meta.cmhc.period, rent.meta.statcan.quarter)}
          </p>
          <nav aria-label={strings.footer.navLabel} className="mt-2 flex flex-wrap gap-x-6">
            <Link href="/how-it-works" className={footerLink}>
              {strings.footer.howItWorks}
            </Link>
            <Link href="/how-it-works#data-and-credits" className={footerLink}>
              {strings.footer.sources}
            </Link>
          </nav>
        </div>
      </footer>
    </>
  );
}

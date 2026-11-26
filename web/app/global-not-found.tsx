// The page for an address that matches no route (M5.3b). The site has two root layouts (French
// and English), so there is no single layout for a 404: this page stands alone (Next.js
// global-not-found, next.config.ts experimental.globalNotFound). It speaks French first (the
// site's default) and English below, each linking to its own search.
import type { Metadata } from "next";
import { Public_Sans } from "next/font/google";
import { PATHS } from "@/lib/routes";
import { en, fr } from "@/lib/strings";
import "./globals.css";

const publicSans = Public_Sans({ variable: "--font-public-sans", subsets: ["latin"] });

export const metadata: Metadata = { title: `${fr.notFound.title} · ${en.notFound.title}` };

const link = "inline-flex min-h-11 items-center font-semibold text-link underline";

export default function GlobalNotFound() {
  return (
    <html lang={fr.meta.htmlLang} className={`${publicSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">
        <main className="mx-auto w-full max-w-2xl flex-1 px-4 pt-8 pb-16 sm:pt-12">
          <h1 className="text-2xl leading-tight font-semibold tracking-tight">{fr.notFound.title}</h1>
          <p className="mt-3">{fr.notFound.text}</p>
          <p className="mt-2">
            <a href={PATHS.fr.home} className={link}>
              {fr.notFound.home}
            </a>
          </p>
          <div lang={en.meta.htmlLang} className="mt-10 border-t border-line pt-8">
            <h2 className="text-lg font-semibold">{en.notFound.title}</h2>
            <p className="mt-3">{en.notFound.text}</p>
            <p className="mt-2">
              <a href={PATHS.en.home} className={link}>
                {en.notFound.home}
              </a>
            </p>
          </div>
        </main>
      </body>
    </html>
  );
}

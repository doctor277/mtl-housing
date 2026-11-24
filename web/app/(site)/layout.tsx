// Shared frame of the site's pages (form, results). The map (/map) runs full screen without it.
import Link from "next/link";
import { strings } from "@/lib/strings";

export default function SiteLayout({ children }: LayoutProps<"/">) {
  return (
    <>
      <header className="border-b border-line">
        <div className="mx-auto flex h-14 w-full max-w-2xl items-center px-4">
          <Link href="/" className="font-semibold tracking-tight no-underline">
            {strings.siteName}
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-2xl flex-1 px-4 pt-8 pb-16 sm:pt-12">{children}</main>
    </>
  );
}

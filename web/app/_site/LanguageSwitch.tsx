"use client";
// The header link to the same page in the other language (owner's M5 decision 7): it keeps the
// current search, and there is no automatic redirect. A plain link: each language has its own
// root layout, so the switch is a full page load. Without JavaScript it still goes to the twin
// page, only without the search; with it, the current query (kept up to date as the sort, view
// and address bar change) is added.
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import type { Lang } from "@/lib/localized";
import { switchPath } from "@/lib/routes";

const linkClass = "inline-flex min-h-11 items-center font-semibold text-link underline";

function SwitchLink({ href, label, toLang }: { href: string; label: string; toLang: Lang }) {
  return (
    <a href={href} hrefLang={toLang} lang={toLang} className={linkClass}>
      {label}
    </a>
  );
}

function WithQuery({ label, toLang }: { label: string; toLang: Lang }) {
  const pathname = usePathname();
  const query = useSearchParams().toString();
  return <SwitchLink href={switchPath(pathname, query ? `?${query}` : "")} label={label} toLang={toLang} />;
}

function WithoutQuery({ label, toLang }: { label: string; toLang: Lang }) {
  return <SwitchLink href={switchPath(usePathname(), "")} label={label} toLang={toLang} />;
}

export default function LanguageSwitch({ label, toLang }: { lang: Lang; label: string; toLang: Lang }) {
  return (
    <Suspense fallback={<WithoutQuery label={label} toLang={toLang} />}>
      <WithQuery label={label} toLang={toLang} />
    </Suspense>
  );
}

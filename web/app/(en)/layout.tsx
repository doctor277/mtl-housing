// Root layout of the English site, under /en (owner's M5 decision 7). French has its own root
// layout at /; switching between them is a full page load.
import SiteFrame from "../_site/SiteFrame";
import { siteMetadata } from "../_site/metadata";

export const metadata = siteMetadata("en");

export default function EnglishLayout({ children }: { children: React.ReactNode }) {
  return <SiteFrame lang="en">{children}</SiteFrame>;
}

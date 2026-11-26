// Root layout of the French site, the default at / (owner's M5 decision 7). English has its
// own root layout under /en; switching between them is a full page load.
import SiteFrame from "../_site/SiteFrame";
import { siteMetadata } from "../_site/metadata";

export const metadata = siteMetadata("fr");

export default function FrenchLayout({ children }: { children: React.ReactNode }) {
  return <SiteFrame lang="fr">{children}</SiteFrame>;
}

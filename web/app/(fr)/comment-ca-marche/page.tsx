import HowItWorksPage from "../../_site/HowItWorksPage";
import { pageMetadata } from "../../_site/metadata";
import { fr } from "@/lib/strings";

export const metadata = pageMetadata("fr", "howItWorks", `${fr.howItWorks.title} · ${fr.siteName}`);

export default function Page() {
  return <HowItWorksPage lang="fr" />;
}

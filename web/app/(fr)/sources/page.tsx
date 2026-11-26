import { pageMetadata } from "../../_site/metadata";
import SourcesPage from "../../_site/SourcesPage";
import { fr } from "@/lib/strings";

export const metadata = pageMetadata("fr", "sources", `${fr.sources.title} · ${fr.siteName}`);

export default function Page() {
  return <SourcesPage lang="fr" />;
}

import { pageMetadata } from "../../../_site/metadata";
import SourcesPage from "../../../_site/SourcesPage";
import { en } from "@/lib/strings";

export const metadata = pageMetadata("en", "sources", `${en.sources.title} · ${en.siteName}`);

export default function Page() {
  return <SourcesPage lang="en" />;
}

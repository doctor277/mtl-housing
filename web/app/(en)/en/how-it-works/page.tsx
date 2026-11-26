import HowItWorksPage from "../../../_site/HowItWorksPage";
import { pageMetadata } from "../../../_site/metadata";
import { en } from "@/lib/strings";

export const metadata = pageMetadata("en", "howItWorks", `${en.howItWorks.title} · ${en.siteName}`);

export default function Page() {
  return <HowItWorksPage lang="en" />;
}

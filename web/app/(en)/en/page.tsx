import HomePage from "../../_site/HomePage";
import { pageMetadata } from "../../_site/metadata";

export const metadata = pageMetadata("en", "home");

export default function Page() {
  return <HomePage lang="en" />;
}

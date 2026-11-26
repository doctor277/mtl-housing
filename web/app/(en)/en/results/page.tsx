import ResultsPage, { resultsMetadata } from "../../../_site/ResultsPage";

export function generateMetadata({ searchParams }: PageProps<"/en/results">) {
  return resultsMetadata("en", searchParams);
}

export default function Page({ searchParams }: PageProps<"/en/results">) {
  return <ResultsPage lang="en" searchParams={searchParams} />;
}

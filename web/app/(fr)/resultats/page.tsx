import ResultsPage, { resultsMetadata } from "../../_site/ResultsPage";

export function generateMetadata({ searchParams }: PageProps<"/resultats">) {
  return resultsMetadata("fr", searchParams);
}

export default function Page({ searchParams }: PageProps<"/resultats">) {
  return <ResultsPage lang="fr" searchParams={searchParams} />;
}

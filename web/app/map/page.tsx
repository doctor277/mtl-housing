// The map of commutes and rents (M1–M3). Not the home page: the search form is (M4). In M4.3
// it becomes the results' second view.
import type { Metadata } from "next";
import { strings } from "@/lib/strings";
import MapView from "../MapView";

export const metadata: Metadata = { title: strings.meta.mapTitle };

export default function MapPage() {
  return <MapView />;
}

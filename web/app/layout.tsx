import type { Metadata } from "next";
import { Public_Sans } from "next/font/google";
import { strings } from "@/lib/strings";
import "./globals.css";

// One family for the whole UI (web/DESIGN.md): Public Sans, self-hosted by next/font at build.
const publicSans = Public_Sans({
  variable: "--font-public-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: strings.meta.title,
  description: strings.meta.description,
  // Link previews: text only, no image (M5 decision 4).
  openGraph: {
    title: strings.meta.title,
    description: strings.meta.description,
    type: "website",
    siteName: strings.siteName,
  },
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang={strings.lang} className={`${publicSans.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col">{children}</body>
    </html>
  );
}

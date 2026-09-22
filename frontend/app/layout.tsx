import type { Metadata } from "next";
import { Geist, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import { LICENCE } from "@/lib/copy/wording";
import "./globals.css";

const sans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const serif = Source_Serif_4({ variable: "--font-source-serif", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "LeaseLens Toronto", template: "%s · LeaseLens Toronto" },
  description:
    "Look up a Toronto apartment building before you sign a lease: City evaluations, building permits and their history, with the source and date of every record.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en-CA" className={`${sans.variable} ${serif.variable} h-full antialiased`}>
      <body className="flex min-h-full flex-col font-sans">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:m-2 focus:rounded focus:bg-card focus:p-2">
          Skip to content
        </a>
        <header className="border-b border-line bg-card">
          <nav aria-label="Main" className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" className="font-serif text-lg font-semibold tracking-tight">
              LeaseLens <span className="text-muted">Toronto</span>
            </Link>
            <Link href="/about-data" className="text-sm text-muted underline-offset-4 hover:text-ink hover:underline">
              About the data
            </Link>
          </nav>
        </header>
        <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
          {children}
        </main>
        <footer className="border-t border-line bg-card">
          <div className="mx-auto max-w-5xl space-y-2 px-4 py-6 text-sm text-muted">
            <p>{LICENCE}</p>
            <p>
              LeaseLens organizes public records. It doesn&apos;t rate buildings or landlords, and it isn&apos;t
              legal advice.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}

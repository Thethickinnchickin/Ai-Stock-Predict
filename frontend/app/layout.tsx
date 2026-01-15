// app/layout.tsx
import "./globals.css";
import Link from "next/link";
import { IBM_Plex_Mono, Space_Grotesk } from "next/font/google";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-space-grotesk",
});

const plexMono = IBM_Plex_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-plex-mono",
});

export const metadata = {
  title: "AI Stock Predictor",
  description: "Live stock predictions with AI",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${spaceGrotesk.variable} ${plexMono.variable} min-h-screen`}>
        <div className="glass sticky top-0 z-30">
          <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <div className="flex items-center gap-3">
              <span className="glow-ring flex h-10 w-10 items-center justify-center rounded-full border border-emerald-300/40 bg-emerald-400/10 text-emerald-300">
                AI
              </span>
              <div>
                <p className="text-sm uppercase tracking-[0.3em] text-muted">Market Intel</p>
                <h1 className="text-lg font-semibold">AI Stock Predictor</h1>
              </div>
            </div>
            <ul className="flex items-center gap-6 text-sm font-medium text-muted">
              <li>
                <Link className="transition hover:text-white" href="/">Home</Link>
              </li>
              <li>
                <Link className="transition hover:text-white" href="/predict">Predictions</Link>
              </li>
              <li>
                <Link className="transition hover:text-white" href="/results">Results</Link>
              </li>
              <li>
                <Link className="transition hover:text-white" href="/model-report">Model Report</Link>
              </li>
              <li>
                <Link className="transition hover:text-white" href="/api-docs">API Docs</Link>
              </li>
              <li>
                <Link className="transition hover:text-white" href="/about">About</Link>
              </li>
            </ul>
          </nav>
        </div>

        <main className="mx-auto flex w-full max-w-6xl flex-1 flex-col gap-16 px-6 pb-20 pt-16">
          {children}
        </main>

        <footer className="mx-auto w-full max-w-6xl px-6 pb-10">
          <div className="panel-outline flex flex-col gap-3 px-6 py-5 text-sm text-muted">
            <p className="text-xs uppercase tracking-[0.28em] text-accent">Live markets. Smarter signals.</p>
            <div className="flex flex-wrap items-center justify-between gap-4">
              <span>AI Stock Predictor © 2025</span>
              <span className="font-mono text-xs text-muted">FastAPI · GraphQL · Next.js</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}

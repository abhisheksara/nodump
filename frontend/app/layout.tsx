import type { Metadata } from "next";
import "./globals.css";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Signal Engine",
  description: "Personal AI/ML research feed",
};

const NAV = [
  { href: "/", label: "Queue" },
  { href: "/saved", label: "Saved" },
  { href: "/history", label: "History" },
  { href: "/settings", label: "Settings" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-zinc-950 text-zinc-200">
        <header className="border-b border-zinc-800 sticky top-0 z-10 bg-zinc-950/80 backdrop-blur">
          <nav className="max-w-3xl mx-auto px-4 h-14 flex items-center gap-6">
            <span className="font-semibold text-zinc-100 mr-4">Signal</span>
            {NAV.map(({ href, label }) => (
              <Link
                key={href}
                href={href}
                className="text-sm text-zinc-400 hover:text-zinc-100 transition-colors"
              >
                {label}
              </Link>
            ))}
          </nav>
        </header>
        <main className="max-w-3xl mx-auto px-4 py-8">{children}</main>
      </body>
    </html>
  );
}

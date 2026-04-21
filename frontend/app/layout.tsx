import type { Metadata, Viewport } from "next";
import { BondPaper } from "@/components/bond-paper";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "ClauseGuard — AI Contract Review for Everyone Else",
    template: "%s · ClauseGuard",
  },
  description:
    "Upload a contract. Get an instant, plain-English risk breakdown and AI-suggested redlines. Built for founders, freelancers, and small teams.",
  applicationName: "ClauseGuard",
  authors: [{ name: "ClauseGuard" }],
  keywords: [
    "contract review",
    "legal AI",
    "NDA review",
    "MSA analysis",
    "redline",
    "risk assessment",
  ],
  openGraph: {
    title: "ClauseGuard — AI Contract Review",
    description:
      "Instant, plain-English contract analysis with AI-suggested redlines.",
    type: "website",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f7f5ef" },
    { media: "(prefers-color-scheme: dark)", color: "#141613" },
  ],
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="relative min-h-screen bg-background text-foreground antialiased">
        <div className="pointer-events-none fixed inset-0 z-0">
          <BondPaper />
        </div>
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
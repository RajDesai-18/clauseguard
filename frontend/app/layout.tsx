import type { Metadata, Viewport } from "next";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL("https://clauseguard.dev"),
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
    description: "Instant, plain-English contract analysis with AI-suggested redlines.",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "ClauseGuard - AI Contract Review",
    description: "Instant, plain-English contract analysis with AI-suggested redlines.",
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
      <body className="bg-background text-foreground relative min-h-screen antialiased">
        <ThemeProvider
          attribute="class"
          defaultTheme="light"
          enableSystem
          disableTransitionOnChange
        >
          <div className="relative z-10">{children}</div>
        </ThemeProvider>
      </body>
    </html>
  );
}

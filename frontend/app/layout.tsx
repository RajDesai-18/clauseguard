import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const spaceGrotesk = localFont({
  src: [
    { path: "../public/fonts/SpaceGrotesk-Regular.woff2", weight: "400" },
    { path: "../public/fonts/SpaceGrotesk-Medium.woff2", weight: "500" },
    { path: "../public/fonts/SpaceGrotesk-SemiBold.woff2", weight: "600" },
    { path: "../public/fonts/SpaceGrotesk-Bold.woff2", weight: "700" },
  ],
  variable: "--font-display",
  display: "swap",
});

const outfit = localFont({
  src: [
    { path: "../public/fonts/Outfit-Light.woff2", weight: "300" },
    { path: "../public/fonts/Outfit-Regular.woff2", weight: "400" },
    { path: "../public/fonts/Outfit-Medium.woff2", weight: "500" },
    { path: "../public/fonts/Outfit-SemiBold.woff2", weight: "600" },
    { path: "../public/fonts/Outfit-Bold.woff2", weight: "700" },
  ],
  variable: "--font-body",
  display: "swap",
});

const azeretMono = localFont({
  src: [
    { path: "../public/fonts/AzeretMono-Light.woff2", weight: "300" },
    { path: "../public/fonts/AzeretMono-Regular.woff2", weight: "400" },
    { path: "../public/fonts/AzeretMono-Medium.woff2", weight: "500" },
    { path: "../public/fonts/AzeretMono-SemiBold.woff2", weight: "600" },
    { path: "../public/fonts/AzeretMono-Bold.woff2", weight: "700" },
  ],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "ClauseGuard - AI-Powered Contract Review",
  description:
    "Instant, plain-English risk analysis for your contracts. Upload NDAs, MSAs, SOWs and get clause-by-clause breakdowns with AI-suggested redlines.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${outfit.variable} ${azeretMono.variable} dark`}
    >
      <body className="font-body bg-background text-foreground antialiased">
        {children}
      </body>
    </html>
  );
}
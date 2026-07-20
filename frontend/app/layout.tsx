import type { Metadata } from "next";
import { Source_Serif_4, IBM_Plex_Sans, IBM_Plex_Mono } from "next/font/google";
import StatusIndicator from "@/components/StatusIndicator";
import "./globals.css";

const sourceSerif4 = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  weight: "variable",
  style: ["normal", "italic"],
  axes: ["opsz"],
});

const ibmPlexSans = IBM_Plex_Sans({
  variable: "--font-ibm-plex-sans",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

const ibmPlexMono = IBM_Plex_Mono({
  variable: "--font-ibm-plex-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Alpha-Guard | Forensic Credit Risk Platform",
  description:
    "Professional-grade forensic credit risk analysis. Altman Z-Score, Monte Carlo simulations, and real-time SEC EDGAR data.",
  keywords: [
    "credit risk",
    "Altman Z-Score",
    "financial analysis",
    "Monte Carlo",
    "SEC EDGAR",
    "forensic finance",
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${sourceSerif4.variable} ${ibmPlexSans.variable} ${ibmPlexMono.variable} antialiased`}
        style={{ background: "var(--paper)", color: "var(--ink)" }}
      >
        {children}
        <StatusIndicator />
      </body>
    </html>
  );
}

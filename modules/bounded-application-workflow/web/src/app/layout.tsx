import type { Metadata } from "next";
import { Cormorant_Garamond, Manrope } from "next/font/google";

import { CopilotProvider } from "@/components/CopilotProvider";

import "./globals.css";

const manrope = Manrope({
  subsets: ["latin"],
  variable: "--font-manrope",
});

const cormorant = Cormorant_Garamond({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-cormorant",
});

export const metadata: Metadata = {
  title: "Skaut Careers",
  description:
    "Navigate your professional life with clarity. Evaluate IT job postings against your profile — deliberate decisions, not application volume.",
  icons: {
    icon: "/logo.png",
    apple: "/logo.png",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${manrope.variable} ${cormorant.variable} antialiased`}>
        <CopilotProvider>{children}</CopilotProvider>
      </body>
    </html>
  );
}

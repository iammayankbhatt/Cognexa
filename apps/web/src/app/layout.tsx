import type { Metadata } from "next";
import { Geist, JetBrains_Mono } from "next/font/google";

import { Providers } from "@/components/providers";
import { ThemeScript } from "@/components/theme/theme-script";
import "./globals.css";

const geist = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const jetbrainsMono = JetBrains_Mono({ variable: "--font-jetbrains-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Cognexa", template: "%s · Cognexa" },
  description:
    "A knowledge-graph-grounded AI tutor for Data Structures & Algorithms with adaptive recommendations.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    // suppressHydrationWarning: ThemeScript sets data-theme before React hydrates.
    <html
      lang="en"
      data-theme="neon-noir"
      suppressHydrationWarning
      className={`${geist.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        <ThemeScript />
      </head>
      <body className="min-h-dvh">
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

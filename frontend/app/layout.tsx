import type { Metadata } from "next";
import localFont from "next/font/local";
import "katex/dist/katex.min.css";
import "./globals.css";

const inter = localFont({ src: "../node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2", variable: "--font-inter", display: "swap" });
const fraunces = localFont({ src: "../node_modules/@fontsource-variable/fraunces/files/fraunces-latin-wght-normal.woff2", variable: "--font-fraunces", display: "swap" });

export const metadata: Metadata = { title: "Khollelab", description: "La salle de colle, autrement." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="fr" className={`${inter.variable} ${fraunces.variable}`}><body>{children}</body></html>;
}

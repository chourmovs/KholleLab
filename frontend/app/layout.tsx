import type { Metadata } from "next";
import localFont from "next/font/local";
import "katex/dist/katex.min.css";
import "./globals.css";

const inter = localFont({ src: "../node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2", variable: "--font-inter", display: "swap" });
const fraunces = localFont({ src: "../node_modules/@fontsource-variable/fraunces/files/fraunces-latin-wght-normal.woff2", variable: "--font-fraunces", display: "swap" });

export const metadata: Metadata = {
  title: "KHOLLELAB",
  description: "La salle de colle, autrement.",
  manifest: "/manifest.webmanifest",
  icons: {icon: [{url: "/assets/brand/favicon.ico"}, {url: "/assets/brand/khollelab-icon-32.png", sizes: "32x32", type: "image/png"}], apple: "/assets/brand/apple-touch-icon.png"},
};
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="fr" className={`${inter.variable} ${fraunces.variable}`}><body>{children}</body></html>;
}

import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const jetbrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  display: "swap",
});

const description =
  "Put your idle Claude Code or Codex subscription to work — read-only reviews " +
  "of your projects while you're busy, one digest every morning.";

/**
 * Where this site actually answers.
 *
 * `metadataBase` prefixes every absolute URL in the page metadata, and og:image
 * is the one that matters: a crawler fetches the card from whatever this says,
 * not from the page it found. It said `https://nightaudit.dev` — a domain that
 * has never been registered — while the site served happily from Railway. The
 * card rendered, the page was fine, and every unfurl asked a nameserver that
 * does not exist. A hardcoded aspiration looks exactly like working config
 * until someone shares the link, which is why it survived this long.
 *
 * So it comes from the platform now rather than from intent. Railway sets
 * `RAILWAY_PUBLIC_DOMAIN`; `NEXT_PUBLIC_SITE_URL` overrides it and is the one
 * switch to flip if a custom domain lands — set it there, change nothing here.
 * The literal is last and is the current deployment, so the worst case is the
 * URL that works today rather than one that never did.
 */
const siteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ||
  (process.env.RAILWAY_PUBLIC_DOMAIN &&
    `https://${process.env.RAILWAY_PUBLIC_DOMAIN}`) ||
  "https://nightshift-site-production.up.railway.app";

export const metadata: Metadata = {
  metadataBase: new URL(siteUrl),
  title: "nightaudit — an audit doesn't change the books",
  description,
  openGraph: {
    title: "nightaudit",
    description,
    url: siteUrl,
    siteName: "nightaudit",
    type: "website",
  },
  twitter: { card: "summary_large_image", title: "nightaudit", description },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html
      lang="en"
      className={`${spaceGrotesk.variable} ${jetbrainsMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}

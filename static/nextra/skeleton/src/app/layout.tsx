import type { Metadata } from "next";
import { Layout, Navbar } from "nextra-theme-docs";
import { Head } from "nextra/components";
import { getPageMap } from "nextra/page-map";
import "./globals.css";
import { Geist, Geist_Mono } from "next/font/google";

export const metadata: Metadata = {
  title: "Your Nextra docs app title",
  description: "Your Nextra docs app description",
};
const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const navbar = <Navbar logo={<b>Nextra</b>} />;

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" dir="ltr" suppressHydrationWarning>
      <Head
        backgroundColor={{ dark: "#09090b", light: "#fafafa" }}
        color={{
          hue: {
            dark: 216,
            light: 221,
          },
          saturation: {
            dark: 100,
            light: 100,
          },
          lightness: {
            dark: 58,
            light: 46,
          },
        }}
      ></Head>
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <Layout
          navbar={navbar}
          pageMap={await getPageMap()}
          docsRepositoryBase="https://github.com/your-repo/edit/main"
        >
          {children}
        </Layout>
      </body>
    </html>
  );
}

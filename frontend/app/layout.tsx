import type { Metadata } from "next";
import "./globals.css";
import { ThemeProvider } from "@/components/ThemeProvider";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { profile } from "@/data/profile";

export const metadata: Metadata = {
  title: `${profile.name} ${profile.surname} — ${profile.title}`,
  description: `Portfolio ${profile.name} ${profile.surname}, ${profile.title}. ${profile.bio.slice(0, 150)}`,
  keywords: [
    "Civil Engineer",
    "Structural Engineer",
    "Data Analyst",
    "Python Developer",
    profile.name,
    "MS Tower",
    "Tower Design",
    "Portfolio",
  ],
  authors: [{ name: `${profile.name} ${profile.surname}` }],
  openGraph: {
    title: `${profile.name} ${profile.surname} — ${profile.title}`,
    description: profile.bio.slice(0, 160),
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="id" suppressHydrationWarning>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
      </head>
      <body>
        <ThemeProvider>
          <Navbar />
          <main>{children}</main>
          <Footer />
        </ThemeProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { JetBrains_Mono } from "next/font/google";
import "./globals.css";
import BottomNav from "@/components/BottomNav";

const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "The Digital Sentinel - Dashboard",
  description: "AI Observability Main Dashboard",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${jetbrainsMono.className} bg-cyber-darker text-cyber-light font-mono min-h-screen pb-16 selection:bg-cyber-cyan selection:text-cyber-darker`}>
        {children}
        <BottomNav />
      </body>
    </html>
  );
}
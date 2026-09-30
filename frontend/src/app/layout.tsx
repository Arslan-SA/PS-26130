import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/components/auth/AuthProvider";
import { Navbar } from "@/components/navigation/Navbar";

export const metadata: Metadata = {
  title: "UdyamSetu AI — Intelligent Industrial Approval & Compliance Platform",
  description: "Unified AI-assisted Single-Window platform for MSME and Industrial regulatory approvals, statutory compliance tracking, and government incentive schemes (SIH26130).",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased font-sans flex flex-col min-h-screen">
        <AuthProvider>
          <Navbar />
          <main className="flex-1">{children}</main>
          <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
            <p>© 2026 UdyamSetu AI · Intelligent Industrial Approval & Compliance Platform · SIH 2026 Prototype</p>
            <p className="mt-1 text-slate-400">Illustrative government regulatory guidance prototype. Not an official statutory portal.</p>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

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
        <header className="border-b border-slate-200 bg-white sticky top-0 z-50 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="h-9 w-9 bg-gov-blue text-white rounded-md flex items-center justify-center font-bold text-lg shadow-sm">
                US
              </div>
              <div>
                <span className="text-xl font-bold text-slate-900 tracking-tight">UdyamSetu<span className="text-gov-sky"> AI</span></span>
                <span className="ml-2.5 px-2 py-0.5 text-xs font-semibold bg-amber-100 text-amber-800 rounded border border-amber-200">
                  SIH26130
                </span>
              </div>
            </div>
            <nav className="flex items-center space-x-6 text-sm font-medium text-slate-600">
              <a href="#features" className="hover:text-gov-blue transition-colors">Features</a>
              <a href="#workflow" className="hover:text-gov-blue transition-colors">Workflow</a>
              <a href="#roles" className="hover:text-gov-blue transition-colors">Roles</a>
              <a href="/login" className="px-4 py-2 bg-gov-blue text-white rounded-md hover:bg-slate-800 transition-colors shadow-sm">
                Portal Login
              </a>
            </nav>
          </div>
        </header>

        <main className="flex-1">{children}</main>

        <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500">
          <p>© 2026 UdyamSetu AI · Intelligent Industrial Approval & Compliance Platform · SIH 2026 Prototype</p>
          <p className="mt-1 text-slate-400">Illustrative government regulatory guidance prototype. Not an official statutory portal.</p>
        </footer>
      </body>
    </html>
  );
}

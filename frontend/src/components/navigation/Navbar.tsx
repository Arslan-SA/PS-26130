"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth/AuthProvider";

export function Navbar() {
  const { user, logout } = useAuth();

  const getDashboardPath = () => {
    if (!user) return "/login";
    switch (user.role) {
      case "INDUSTRY_USER":
        return "/dashboard";
      case "DEPARTMENT_OFFICER":
        return "/officer/inbox";
      case "INSPECTOR":
        return "/inspector/schedule";
      case "ADMIN":
        return "/admin";
      default:
        return "/dashboard";
    }
  };

  const getRoleBadge = () => {
    if (!user) return null;
    switch (user.role) {
      case "INDUSTRY_USER":
        return <span className="px-2 py-0.5 text-xs font-semibold bg-blue-100 text-blue-800 rounded">Industry</span>;
      case "DEPARTMENT_OFFICER":
        return <span className="px-2 py-0.5 text-xs font-semibold bg-emerald-100 text-emerald-800 rounded">Officer</span>;
      case "INSPECTOR":
        return <span className="px-2 py-0.5 text-xs font-semibold bg-amber-100 text-amber-800 rounded">Inspector</span>;
      case "ADMIN":
        return <span className="px-2 py-0.5 text-xs font-semibold bg-purple-100 text-purple-800 rounded">Admin</span>;
    }
  };

  return (
    <header className="border-b border-slate-200 bg-white sticky top-0 z-50 shadow-sm">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center space-x-3 group">
          <div className="h-9 w-9 bg-gov-blue text-white rounded-md flex items-center justify-center font-bold text-lg shadow-sm group-hover:bg-slate-800 transition-colors">
            US
          </div>
          <div>
            <span className="text-xl font-bold text-slate-900 tracking-tight">
              UdyamSetu<span className="text-gov-sky"> AI</span>
            </span>
            <span className="ml-2.5 px-2 py-0.5 text-xs font-semibold bg-amber-100 text-amber-800 rounded border border-amber-200">
              SIH26130
            </span>
          </div>
        </Link>

        <nav className="flex items-center space-x-5 text-sm font-medium text-slate-600">
          <Link href="/#features" className="hover:text-gov-blue transition-colors hidden md:inline-block">
            Features
          </Link>
          <Link href="/#workflow" className="hover:text-gov-blue transition-colors hidden md:inline-block">
            Workflow
          </Link>
          <Link href="/#roles" className="hover:text-gov-blue transition-colors hidden md:inline-block">
            Roles
          </Link>

          {user ? (
            <div className="flex items-center space-x-3">
              <Link
                href={getDashboardPath()}
                className="px-3.5 py-1.5 bg-gov-blue text-white rounded-md hover:bg-slate-800 transition-colors shadow-sm text-xs font-semibold flex items-center space-x-1.5"
              >
                <span>Dashboard</span>
                {getRoleBadge()}
              </Link>
              <div className="text-xs text-slate-700 hidden sm:block font-medium truncate max-w-[120px]">
                {user.full_name}
              </div>
              <button
                onClick={logout}
                className="px-3 py-1.5 border border-slate-300 text-slate-600 rounded-md hover:bg-slate-100 transition-colors text-xs font-medium"
              >
                Sign Out
              </button>
            </div>
          ) : (
            <Link
              href="/login"
              className="px-4 py-2 bg-gov-blue text-white rounded-md hover:bg-slate-800 transition-colors shadow-sm text-xs font-semibold"
            >
              Portal Login
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}

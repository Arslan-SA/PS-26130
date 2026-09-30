"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "@/components/auth/AuthProvider";

export default function UnauthorizedPage() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-[75vh] flex items-center justify-center bg-slate-50 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full bg-white p-8 rounded-xl shadow-md border border-slate-200 text-center">
        <div className="h-16 w-16 bg-amber-100 text-amber-700 rounded-full flex items-center justify-center font-bold text-2xl mx-auto mb-4 border border-amber-200">
          !
        </div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Access Restricted</h1>
        <p className="mt-2 text-sm text-slate-600">
          Your current account role does not have statutory clearance permissions to access this specific portal resource.
        </p>

        {user && (
          <div className="mt-4 p-3 bg-slate-50 rounded border border-slate-200 text-left text-xs space-y-1">
            <p><span className="font-semibold text-slate-700">Authenticated As:</span> {user.full_name} ({user.email})</p>
            <p><span className="font-semibold text-slate-700">Active Role:</span> <span className="font-mono bg-slate-200 px-1.5 py-0.5 rounded text-slate-800">{user.role}</span></p>
          </div>
        )}

        <div className="mt-6 flex flex-col sm:flex-row gap-3 justify-center">
          <Link
            href="/"
            className="px-4 py-2 bg-gov-blue text-white rounded-md text-sm font-medium hover:bg-slate-800 transition-colors"
          >
            Return to Portal Home
          </Link>
          <button
            onClick={logout}
            className="px-4 py-2 border border-slate-300 text-slate-700 rounded-md text-sm font-medium hover:bg-slate-50 transition-colors"
          >
            Switch Account
          </button>
        </div>
      </div>
    </div>
  );
}

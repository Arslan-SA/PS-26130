"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Business, fetchUserBusinesses } from "@/lib/business";
import { DependencyGraphResponse, getDependencyGraph } from "@/lib/approvals";
import DependencyGraphView from "@/components/approvals/DependencyGraphView";

export default function ApprovalsGraphPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [graph, setGraph] = useState<DependencyGraphResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const businesses = await fetchUserBusinesses();
        if (businesses && businesses.length > 0) {
          const biz = businesses[0];
          setBusiness(biz);
          const g = await getDependencyGraph(biz.id);
          setGraph(g);
        }
      } catch (err: any) {
        console.error("Failed to load clearance DAG graph:", err);
        setErrorMsg(err.message || "Failed to retrieve clearance dependency graph.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <ProtectedRoute allowedRoles={["INDUSTRY_USER", "DEPARTMENT_OFFICER", "ADMIN"]}>
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Header Banner */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md">
            <div>
              <div className="flex items-center gap-3">
                <span className="p-2 rounded-lg bg-indigo-900/40 text-indigo-400 border border-indigo-700/40">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                  </svg>
                </span>
                <div>
                  <h1 className="text-2xl font-bold text-white tracking-tight">
                    Clearance Dependency DAG & Critical Path
                  </h1>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {business ? `${business.legal_name} • Topological Sequencing Architecture` : "Statutory Sequence DAG"}
                  </p>
                </div>
              </div>
            </div>

            {/* View Switcher Toggle */}
            <div className="flex items-center gap-2 bg-slate-950/80 p-1.5 rounded-xl border border-slate-800">
              <Link
                href="/approvals"
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition-colors"
              >
                Cards View
              </Link>
              <span className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white shadow-sm">
                Dependency DAG
              </span>
            </div>
          </div>

          {/* Error Banner */}
          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm">
              {errorMsg}
            </div>
          )}

          {/* Content */}
          {loading ? (
            <div className="p-16 text-center text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-700 border-t-indigo-500 mb-4"></div>
              <p className="text-sm">Calculating topological execution order and critical path...</p>
            </div>
          ) : graph ? (
            <DependencyGraphView graph={graph} />
          ) : (
            <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400">
              No clearance dependencies to visualize for this enterprise.
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}

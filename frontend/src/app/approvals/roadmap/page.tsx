"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Business, fetchUserBusinesses } from "@/lib/business";
import { RoadmapPlan, getClearanceRoadmap } from "@/lib/approvals";
import PersonalizedRoadmapView from "@/components/approvals/PersonalizedRoadmapView";

export default function ApprovalsRoadmapPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [plan, setPlan] = useState<RoadmapPlan | null>(null);
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
          const p = await getClearanceRoadmap(biz.id);
          setPlan(p);
        }
      } catch (err: any) {
        console.error("Failed to load clearance roadmap:", err);
        setErrorMsg(err.message || "Failed to retrieve clearance roadmap.");
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
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </span>
                <div>
                  <h1 className="text-2xl font-bold text-white tracking-tight">
                    Personalized Regulatory Timeline & Roadmap
                  </h1>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {business ? `${business.legal_name} • Lifecycle Gantt Progression` : "Clearance Execution Timeline"}
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
              <Link
                href="/approvals/graph"
                className="px-3.5 py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition-colors"
              >
                DAG Graph
              </Link>
              <span className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white shadow-sm">
                Roadmap Gantt
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
              <p className="text-sm">Calculating milestone phase dates and statutory forward pass...</p>
            </div>
          ) : plan ? (
            <PersonalizedRoadmapView plan={plan} />
          ) : (
            <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400">
              No clearance roadmap available for this business unit.
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}

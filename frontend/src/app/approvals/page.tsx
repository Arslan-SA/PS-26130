"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { Business, fetchUserBusinesses } from "@/lib/business";
import {
  ApprovalRequirement,
  ClearanceSummary,
  RequirementStage,
  discoverApprovals,
  getBusinessRequirements,
  getClearanceSummary,
} from "@/lib/approvals";
import ApprovalRecommendationCard from "@/components/approvals/ApprovalRecommendationCard";

export default function ApprovalsRecommendationPage() {
  const [business, setBusiness] = useState<Business | null>(null);
  const [requirements, setRequirements] = useState<ApprovalRequirement[]>([]);
  const [summary, setSummary] = useState<ClearanceSummary | null>(null);
  const [selectedStage, setSelectedStage] = useState<string>("ALL");
  const [loading, setLoading] = useState<boolean>(true);
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const businesses = await fetchUserBusinesses();
        if (businesses && businesses.length > 0) {
          const biz = businesses[0];
          setBusiness(biz);

          // Attempt loading existing requirements first
          const existing = await getBusinessRequirements(biz.id);
          if (existing && existing.length > 0) {
            setRequirements(existing);
            const sum = await getClearanceSummary(biz.id);
            setSummary(sum);
          } else {
            // First time: run statutory discovery automatically
            const disc = await discoverApprovals(biz.id);
            setRequirements(disc.requirements);
            setSummary(disc.summary);
          }
        }
      } catch (err: any) {
        console.error("Failed to load statutory approvals:", err);
        setErrorMsg(err.message || "Failed to retrieve regulatory clearances.");
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const handleReevaluate = async () => {
    if (!business) return;
    try {
      setEvaluating(true);
      setErrorMsg(null);
      const disc = await discoverApprovals(business.id);
      setRequirements(disc.requirements);
      setSummary(disc.summary);
    } catch (err: any) {
      console.error("Re-evaluation failed:", err);
      setErrorMsg(err.message || "Rule evaluation failed.");
    } finally {
      setEvaluating(false);
    }
  };

  const handleRequirementUpdated = (updated: ApprovalRequirement) => {
    setRequirements((prev) =>
      prev.map((r) => (r.id === updated.id ? updated : r))
    );
  };

  const filteredRequirements = requirements.filter((r) => {
    if (selectedStage === "ALL") return true;
    return r.stage === selectedStage;
  });

  return (
    <ProtectedRoute allowedRoles={["INDUSTRY_USER", "DEPARTMENT_OFFICER", "ADMIN"]}>
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header Banner */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md">
            <div>
              <div className="flex items-center gap-3">
                <span className="p-2 rounded-lg bg-indigo-900/40 text-indigo-400 border border-indigo-700/40">
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </span>
                <div>
                  <h1 className="text-2xl font-bold text-white tracking-tight">
                    Statutory Clearances & Compliance Roadmap
                  </h1>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {business ? `${business.legal_name} • Intelligent Regulatory Clearance Engine` : "Regulatory Clearance Discovery"}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5 bg-slate-950/80 p-1.5 rounded-xl border border-slate-800">
                <span className="px-3.5 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 text-white shadow-sm">
                  Cards
                </span>
                <Link
                  href="/approvals/graph"
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition-colors"
                >
                  DAG Graph
                </Link>
                <Link
                  href="/approvals/roadmap"
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition-colors"
                >
                  Roadmap
                </Link>
                <Link
                  href="/approvals/actions"
                  className="px-3.5 py-1.5 text-xs font-semibold rounded-lg text-slate-400 hover:text-white transition-colors"
                >
                  Next Actions
                </Link>
              </div>

              <button
                onClick={handleReevaluate}
                disabled={evaluating || !business}
                className="inline-flex items-center px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-500 text-white transition-all shadow-md shadow-indigo-600/20"
              >
                {evaluating ? (
                  <>
                    <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    Evaluating Rules...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Re-evaluate Profile
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {errorMsg && (
            <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-sm">
              {errorMsg}
            </div>
          )}

          {/* Metric KPIs */}
          {summary && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl">
                <span className="text-xs text-slate-400 font-medium">Clearances Identified</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-white">{summary.total_requirements}</span>
                  <span className="text-xs font-semibold px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/40">
                    {summary.mandatory_requirements} Mandatory
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-2">
                  CPCB & statutory acts mapped
                </p>
              </div>

              <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl">
                <span className="text-xs text-slate-400 font-medium">Statutory Fee Outlay</span>
                <div className="mt-2 flex items-baseline gap-1">
                  <span className="text-3xl font-bold text-emerald-400">
                    ₹{summary.total_estimated_fee.toLocaleString("en-IN")}
                  </span>
                </div>
                <p className="text-[11px] text-slate-400 mt-2">
                  Direct treasury deposit assessment
                </p>
              </div>

              <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl">
                <span className="text-xs text-slate-400 font-medium">Critical Path SLA</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-3xl font-bold text-indigo-400">
                    {summary.pre_establishment_critical_days}
                  </span>
                  <span className="text-xs text-slate-400">Days</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-2">
                  Pre-establishment turnaround target
                </p>
              </div>

              <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl">
                <span className="text-xs text-slate-400 font-medium">Regulatory Departments</span>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Object.entries(summary.by_department).map(([dept, count]) => (
                    <span
                      key={dept}
                      className="text-[11px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-medium"
                    >
                      {dept}: {count}
                    </span>
                  ))}
                </div>
                <p className="text-[11px] text-slate-400 mt-2">
                  Single-window connected boards
                </p>
              </div>
            </div>
          )}

          {/* Stage Filter Navigation */}
          <div className="flex flex-wrap items-center gap-2 border-b border-slate-800 pb-3">
            {[
              { id: "ALL", label: "All Clearances" },
              { id: "PRE_ESTABLISHMENT", label: "1. Pre-Establishment" },
              { id: "PRE_COMMISSIONING", label: "2. Pre-Commissioning" },
              { id: "POST_COMMISSIONING", label: "3. Post-Commissioning" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setSelectedStage(tab.id)}
                className={`text-xs font-semibold px-4 py-2 rounded-lg transition-all ${
                  selectedStage === tab.id
                    ? "bg-indigo-600 text-white shadow-sm"
                    : "bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800/80"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Recommendations Grid */}
          {loading ? (
            <div className="p-12 text-center text-slate-400">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-700 border-t-indigo-500 mb-4"></div>
              <p className="text-sm">Evaluating statutory clearance rules against your industrial profile...</p>
            </div>
          ) : filteredRequirements.length === 0 ? (
            <div className="p-12 text-center rounded-2xl bg-slate-900/40 border border-slate-800 text-slate-400">
              <p className="text-base font-semibold text-slate-300">No clearances required for this stage.</p>
              <p className="text-xs text-slate-500 mt-1">
                Your industrial unit either holds statutory exemptions or parameters do not trigger this regulatory tier.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {filteredRequirements.map((req) => (
                <ApprovalRecommendationCard
                  key={req.id}
                  requirement={req}
                  onStatusUpdated={handleRequirementUpdated}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}

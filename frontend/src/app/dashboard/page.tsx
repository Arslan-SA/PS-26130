"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/components/auth/AuthProvider";
import { Business, fetchUserBusinesses } from "@/lib/business";

export default function BusinessDashboardPage() {
  const { user } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    async function loadData() {
      try {
        const businesses = await fetchUserBusinesses();
        if (businesses && businesses.length > 0) {
          setBusiness(businesses[0]);
        }
      } catch (err) {
        console.error("Failed to load business profile", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const getPollutionColor = (category?: string | null) => {
    switch (category) {
      case "RED":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "ORANGE":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "GREEN":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "WHITE":
        return "bg-slate-400/10 text-slate-300 border-slate-400/30";
      default:
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
    }
  };

  return (
    <ProtectedRoute allowedRoles={["INDUSTRY_USER", "ADMIN"]}>
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header Banner */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md">
            <div>
              <div className="flex items-center gap-3">
                <h1 className="text-2xl font-bold text-white tracking-tight">
                  {business ? business.legal_name : "Enterprise Single-Window Dashboard"}
                </h1>
                {business?.profile?.pollution_category && (
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border ${getPollutionColor(
                      business.profile.pollution_category
                    )}`}
                  >
                    CPCB {business.profile.pollution_category}
                  </span>
                )}
                {business?.msme_category && (
                  <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold border border-indigo-500/30 bg-indigo-500/10 text-indigo-400">
                    MSME {business.msme_category}
                  </span>
                )}
              </div>
              <p className="text-slate-400 text-sm mt-1">
                Authorized Representative: <span className="text-slate-200 font-medium">{user?.full_name}</span> (
                {user?.email})
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/onboarding"
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-xl border border-slate-700 transition"
              >
                {business ? "Edit Profile" : "Register Unit"}
              </Link>
              <Link
                href="/discovery"
                className="px-5 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white text-sm font-semibold rounded-xl shadow-lg shadow-blue-600/30 transition"
              >
                AI Approval Discovery
              </Link>
            </div>
          </div>

          {/* Metric KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* KPI 1 */}
            <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl relative overflow-hidden">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Profile Completeness
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">
                  {business?.profile ? `${business.profile.profile_completeness}%` : "0%"}
                </span>
                <span className="text-xs text-emerald-400 font-medium">
                  {business?.profile?.is_profile_complete ? "Verified Complete" : "Action Required"}
                </span>
              </div>
              <div className="w-full bg-slate-800 h-1.5 rounded-full mt-3 overflow-hidden">
                <div
                  className="bg-emerald-500 h-full rounded-full transition-all duration-500"
                  style={{ width: `${business?.profile?.profile_completeness || 0}%` }}
                />
              </div>
            </div>

            {/* KPI 2 */}
            <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Statutory Approvals
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">7</span>
                <span className="text-xs text-blue-400 font-medium">Discovered by AI</span>
              </div>
              <p className="text-xs text-slate-500 mt-2">PCB CTE, Factory Inspectorate, Fire NOC, DISCOM</p>
            </div>

            {/* KPI 3 */}
            <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Active Applications
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">2</span>
                <span className="text-xs text-amber-400 font-medium">In Department Review</span>
              </div>
              <p className="text-xs text-slate-500 mt-2">Next SLA deadline: In 4 days</p>
            </div>

            {/* KPI 4 */}
            <div className="p-5 bg-slate-900/60 border border-slate-800 rounded-xl">
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
                Capital Tracked
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-3xl font-extrabold text-white">
                  {business?.profile?.plant_machinery_investment
                    ? `₹${(business.profile.plant_machinery_investment / 10000000).toFixed(1)} Cr`
                    : "—"}
                </span>
                <span className="text-xs text-purple-400 font-medium">Plant & Machinery</span>
              </div>
              <p className="text-xs text-slate-500 mt-2">Eligible for CGTMSE & State PSI</p>
            </div>
          </div>

          {/* Operational Details & Regulatory Status Grid */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Unit Details */}
            <div className="lg:col-span-2 space-y-6">
              <div className="p-6 bg-slate-900/70 border border-slate-800 rounded-2xl">
                <h3 className="text-lg font-bold text-white mb-4 flex items-center justify-between">
                  <span>Industrial Plant Profile</span>
                  <span className="text-xs font-mono text-slate-400">
                    PAN: {business?.pan || "PENDING"}
                  </span>
                </h3>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm">
                  <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    <span className="text-xs text-slate-500 block">Manufacturing Activity</span>
                    <span className="text-slate-200 font-medium mt-0.5 block truncate">
                      {business?.profile?.manufacturing_activity || "Not configured yet"}
                    </span>
                  </div>

                  <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    <span className="text-xs text-slate-500 block">NIC Code (2008)</span>
                    <span className="text-slate-200 font-mono mt-0.5 block">
                      {business?.profile?.nic_code || "Unassigned"}
                    </span>
                  </div>

                  <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    <span className="text-xs text-slate-500 block">Location & Industrial Zone</span>
                    <span className="text-slate-200 font-medium mt-0.5 block truncate">
                      {business?.profile?.industrial_area || business?.profile?.district
                        ? `${business?.profile?.industrial_area || "Independent"}, ${business?.profile?.district}, ${business?.profile?.state}`
                        : "Location pending"}
                    </span>
                  </div>

                  <div className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800/80">
                    <span className="text-xs text-slate-500 block">Connected Power / Water Demand</span>
                    <span className="text-slate-200 font-medium mt-0.5 block">
                      {business?.profile?.power_requirement_kw || 0} kW • {business?.profile?.water_requirement_kld || 0} KLD
                    </span>
                  </div>
                </div>
              </div>

              {/* Action Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <Link
                  href="/documents"
                  className="p-5 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl transition group"
                >
                  <div className="w-10 h-10 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center mb-3">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <h4 className="text-sm font-bold text-white group-hover:text-blue-400 transition">Document Vault & OCR</h4>
                  <p className="text-xs text-slate-400 mt-1">Upload Land deeds, NOCs, PAN, and Site layout for instant AI verification.</p>
                </Link>

                <Link
                  href="/compliance"
                  className="p-5 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl transition group"
                >
                  <div className="w-10 h-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mb-3">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                    </svg>
                  </div>
                  <h4 className="text-sm font-bold text-white group-hover:text-emerald-400 transition">Compliance Calendar</h4>
                  <p className="text-xs text-slate-400 mt-1">Track statutory renewal deadlines, annual returns, and audit schedules.</p>
                </Link>

                <Link
                  href="/schemes"
                  className="p-5 bg-gradient-to-br from-slate-900 to-slate-950 border border-slate-800 hover:border-slate-700 rounded-xl transition group"
                >
                  <div className="w-10 h-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mb-3">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h4 className="text-sm font-bold text-white group-hover:text-indigo-400 transition">Incentives & Schemes</h4>
                  <p className="text-xs text-slate-400 mt-1">Unlock capital subsidies, interest subvention, and credit guarantee schemes.</p>
                </Link>
              </div>
            </div>

            {/* Right 1 Col: Regulatory Notifications & Quick Insights */}
            <div className="p-6 bg-slate-900/70 border border-slate-800 rounded-2xl space-y-4">
              <h3 className="text-base font-bold text-white">Statutory Updates & Alerts</h3>
              <div className="space-y-3">
                <div className="p-3 bg-blue-500/10 border border-blue-500/20 rounded-xl text-xs">
                  <span className="font-semibold text-blue-400 block mb-0.5">CPCB Guideline Update</span>
                  <p className="text-slate-300">White category industries exempted from periodic consent inspection.</p>
                </div>

                <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-xl text-xs">
                  <span className="font-semibold text-amber-400 block mb-0.5">Fire NOC Site Inspection</span>
                  <p className="text-slate-300">Field inspection scheduled by Regional Fire Officer for upcoming week.</p>
                </div>

                <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs">
                  <span className="font-semibold text-emerald-400 block mb-0.5">MSME Capital Subsidy</span>
                  <p className="text-slate-300">Eligible for up to 15% capital reimbursement on plant machinery installation.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

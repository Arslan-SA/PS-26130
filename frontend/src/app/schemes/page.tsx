"use client";

/**
 * Government Schemes & Subsidies Recommendation Dashboard (Phase 8, Fragments 108–111).
 * 
 * Provides an industrial enterprise with:
 * - Unlocked subsidy value & eligibility summary metrics
 * - Smart AI/Rule matched scheme catalog with match score gauges
 * - In-depth criterion audit (Fragment 109)
 * - Document Vault gap analysis (Fragment 110)
 * - Step-by-step application guidance & tracking (Fragment 111)
 */

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/components/auth/AuthProvider";
import { fetchUserBusinesses, Business } from "@/lib/business";
import {
  GovernmentScheme,
  SchemeEvaluationResult,
  BusinessSchemeSummary,
  SchemeApplication,
  SchemeType,
  SchemeApplicationStatus,
  fetchBusinessRecommendations,
  evaluateSchemeForBusiness,
  trackSchemeApplication,
  fetchBusinessSchemeApplications,
  updateSchemeApplication,
  formatINR,
  getSchemeTypeLabel,
  getSchemeTypeBadge,
  getApplicationStatusBadge,
} from "@/lib/schemes";

export default function SchemesPage() {
  const { user } = useAuth();
  const [business, setBusiness] = useState<Business | null>(null);
  const [summary, setSummary] = useState<BusinessSchemeSummary | null>(null);
  const [trackedApplications, setTrackedApplications] = useState<SchemeApplication[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Tabs
  const [activeTab, setActiveTab] = useState<"ALL" | "ELIGIBLE" | "CAPITAL" | "CREDIT" | "GREEN" | "TRACKED">("ALL");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Detailed Modal State
  const [selectedScheme, setSelectedScheme] = useState<SchemeEvaluationResult | null>(null);
  const [modalLoading, setModalLoading] = useState<boolean>(false);
  const [modalTab, setModalTab] = useState<"CRITERIA" | "DOCUMENTS" | "GUIDANCE">("CRITERIA");
  const [trackingNotes, setTrackingNotes] = useState<string>("");
  const [trackingStatus, setTrackingStatus] = useState<SchemeApplicationStatus>("BOOKMARKED");
  const [trackingRef, setTrackingRef] = useState<string>("");
  const [isSavingTracking, setIsSavingTracking] = useState<boolean>(false);
  const [saveSuccessMsg, setSaveSuccessMsg] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const businesses = await fetchUserBusinesses();
      if (!businesses || businesses.length === 0) {
        setBusiness(null);
        setLoading(false);
        return;
      }

      const activeBiz = businesses[0];
      setBusiness(activeBiz);

      // Load recommendations
      const recSummary = await fetchBusinessRecommendations(activeBiz.id);
      setSummary(recSummary);

      // Load tracked applications
      const apps = await fetchBusinessSchemeApplications(activeBiz.id);
      setTrackedApplications(apps);
    } catch (err: any) {
      console.error("Failed to load scheme recommendations", err);
      setError(err.message || "Failed to load government schemes.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Open modal with full gap analysis & guidance
  const openSchemeModal = async (scheme: SchemeEvaluationResult, initialTab: "CRITERIA" | "DOCUMENTS" | "GUIDANCE" = "CRITERIA") => {
    setSelectedScheme(scheme);
    setModalTab(initialTab);
    setSaveSuccessMsg(null);

    // Find if already tracked
    const existing = trackedApplications.find((a) => a.scheme_id === scheme.scheme_id);
    if (existing) {
      setTrackingStatus(existing.status);
      setTrackingNotes(existing.notes || "");
      setTrackingRef(existing.application_reference_number || "");
    } else {
      setTrackingStatus("BOOKMARKED");
      setTrackingNotes("");
      setTrackingRef("");
    }

    // Fetch full evaluation with document gap analysis if not already populated
    if (business && !scheme.document_readiness) {
      try {
        setModalLoading(true);
        const detailed = await evaluateSchemeForBusiness(scheme.scheme_id, business.id);
        setSelectedScheme(detailed);
      } catch (e) {
        console.error("Could not fetch detailed gap analysis", e);
      } finally {
        setModalLoading(false);
      }
    }
  };

  const handleSaveTracking = async () => {
    if (!business || !selectedScheme) return;
    try {
      setIsSavingTracking(true);
      setSaveSuccessMsg(null);
      await trackSchemeApplication(
        business.id,
        selectedScheme.scheme_id,
        trackingStatus,
        trackingNotes,
        trackingRef
      );

      // Reload applications list
      const apps = await fetchBusinessSchemeApplications(business.id);
      setTrackedApplications(apps);
      setSaveSuccessMsg("Scheme milestone updated successfully!");
      setTimeout(() => setSaveSuccessMsg(null), 3000);
    } catch (err: any) {
      console.error("Failed to track scheme", err);
      alert(err.message || "Failed to update tracking milestone.");
    } finally {
      setIsSavingTracking(false);
    }
  };

  // Filter schemes based on active tab & search
  const filteredSchemes = (summary?.schemes || []).filter((s) => {
    // Search match
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const inName = s.scheme_name.toLowerCase().includes(q) || s.short_name.toLowerCase().includes(q);
      const inMinistry = s.ministry.toLowerCase().includes(q);
      const inTags = s.tags.some((t) => t.toLowerCase().includes(q));
      if (!inName && !inMinistry && !inTags) return false;
    }

    // Tab filter
    if (activeTab === "ELIGIBLE") return s.is_eligible;
    if (activeTab === "CAPITAL") return s.scheme_type === "CAPITAL_SUBSIDY" || s.scheme_type === "TECHNOLOGY_UPGRADATION";
    if (activeTab === "CREDIT") return s.scheme_type === "CREDIT_GUARANTEE" || s.scheme_type === "INTEREST_SUBVENTION";
    if (activeTab === "GREEN") return s.scheme_type === "GREEN_INCENTIVE" || s.scheme_type === "QUALITY_CERTIFICATION";
    return true;
  });

  return (
    <ProtectedRoute allowedRoles={["INDUSTRY_USER", "ADMIN"]}>
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Header Banner */}
          <div className="p-6 bg-gradient-to-r from-slate-900 via-indigo-950/60 to-slate-900 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-400 mb-1">
                <span>Government of India & State Industrial Subsidies</span>
                <span>•</span>
                <span className="text-emerald-400">AI Eligibility Engine</span>
              </div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                Incentives & Subsidies Navigator
              </h1>
              <p className="text-slate-400 text-sm mt-1 max-w-2xl">
                Real-time eligibility matching against Central & State schemes for{" "}
                <span className="text-white font-medium">{business?.legal_name || "Your Enterprise"}</span> based on MSME tier, investment, and operational category.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/dashboard"
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-xl border border-slate-700 transition"
              >
                Dashboard
              </Link>
              <button
                onClick={loadData}
                disabled={loading}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold rounded-xl shadow-lg shadow-indigo-600/30 transition flex items-center gap-2"
              >
                <svg className={`w-4 h-4 ${loading ? "animate-spin" : ""}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Re-evaluate</span>
              </button>
            </div>
          </div>

          {/* Metric KPI Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {/* KPI 1: Total Subsidy Potential */}
            <div className="p-5 bg-gradient-to-br from-emerald-950/40 via-slate-900 to-slate-900 border border-emerald-500/30 rounded-xl relative overflow-hidden shadow-lg">
              <div className="text-xs font-semibold uppercase tracking-wider text-emerald-400 mb-1">
                Potential Financial Benefit
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
                {summary ? formatINR(summary.total_subsidy_potential_inr) : "—"}
              </div>
              <div className="text-xs text-slate-400 mt-2 flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-400 inline-block animate-pulse" />
                <span>Across eligible capital & interest subsidies</span>
              </div>
            </div>

            {/* KPI 2: Eligible Schemes */}
            <div className="p-5 bg-gradient-to-br from-indigo-950/40 via-slate-900 to-slate-900 border border-indigo-500/30 rounded-xl relative overflow-hidden shadow-lg">
              <div className="text-xs font-semibold uppercase tracking-wider text-indigo-400 mb-1">
                Eligible Schemes
              </div>
              <div className="flex items-baseline gap-2 mt-1">
                <span className="text-2xl sm:text-3xl font-extrabold text-white">
                  {summary?.total_eligible_schemes ?? 0}
                </span>
                <span className="text-sm text-slate-400">
                  / {summary?.total_schemes_evaluated ?? 0} evaluated
                </span>
              </div>
              <div className="text-xs text-slate-400 mt-2">
                100% hard statutory criteria satisfied
              </div>
            </div>

            {/* KPI 3: Top Match Rating */}
            <div className="p-5 bg-gradient-to-br from-blue-950/40 via-slate-900 to-slate-900 border border-blue-500/30 rounded-xl relative overflow-hidden shadow-lg">
              <div className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-1">
                Highest Match Score
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
                {summary && summary.schemes.length > 0 ? `${summary.schemes[0].match_score}%` : "—"}
              </div>
              <div className="text-xs text-slate-400 mt-2 truncate">
                {summary && summary.schemes.length > 0 ? summary.schemes[0].short_name : "Pending Profile"}
              </div>
            </div>

            {/* KPI 4: Active Applications */}
            <div className="p-5 bg-gradient-to-br from-purple-950/40 via-slate-900 to-slate-900 border border-purple-500/30 rounded-xl relative overflow-hidden shadow-lg">
              <div className="text-xs font-semibold uppercase tracking-wider text-purple-400 mb-1">
                Tracked Applications
              </div>
              <div className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
                {trackedApplications.length}
              </div>
              <div className="text-xs text-slate-400 mt-2">
                Saved for DPR preparation & submission
              </div>
            </div>
          </div>

          {/* Navigation Filter Tabs & Search */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => setActiveTab("ALL")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "ALL"
                    ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                All Schemes ({summary?.schemes.length ?? 0})
              </button>
              <button
                onClick={() => setActiveTab("ELIGIBLE")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "ELIGIBLE"
                    ? "bg-emerald-600 text-white shadow-md shadow-emerald-600/30"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                Directly Eligible ({summary?.total_eligible_schemes ?? 0})
              </button>
              <button
                onClick={() => setActiveTab("CAPITAL")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "CAPITAL"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                Capital Subsidies
              </button>
              <button
                onClick={() => setActiveTab("CREDIT")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "CREDIT"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                Credit & Loans
              </button>
              <button
                onClick={() => setActiveTab("GREEN")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "GREEN"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                Green & Quality (ZED)
              </button>
              <button
                onClick={() => setActiveTab("TRACKED")}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold transition ${
                  activeTab === "TRACKED"
                    ? "bg-purple-600 text-white shadow-md shadow-purple-600/30"
                    : "bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800"
                }`}
              >
                My Applications ({trackedApplications.length})
              </button>
            </div>

            {/* Search Input */}
            <div className="relative min-w-[240px]">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search scheme name, ministry, tags..."
                className="w-full px-3.5 py-2 pl-9 bg-slate-900 border border-slate-800 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
              />
              <svg
                className="w-4 h-4 text-slate-500 absolute left-3 top-2.5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-sm">
              {error}
            </div>
          )}

          {/* Loading Indicator */}
          {loading && (
            <div className="text-center py-20">
              <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-slate-400 text-sm">Running statutory eligibility engine across Central & State catalogs...</p>
            </div>
          )}

          {/* Tracked Applications View */}
          {!loading && activeTab === "TRACKED" && (
            <div className="space-y-4">
              {trackedApplications.length === 0 ? (
                <div className="p-12 text-center bg-slate-900/40 border border-slate-800 rounded-2xl">
                  <div className="w-12 h-12 rounded-full bg-purple-500/10 text-purple-400 flex items-center justify-center mx-auto mb-3">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                    </svg>
                  </div>
                  <h3 className="text-base font-bold text-white">No Tracked Applications Yet</h3>
                  <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto">
                    Browse the recommended schemes catalog and click &ldquo;Bookmark / Track Application&rdquo; to monitor your DPR preparation and sanction status.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {trackedApplications.map((app) => {
                    const badge = getApplicationStatusBadge(app.status);
                    return (
                      <div
                        key={app.id}
                        className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl space-y-3 hover:border-slate-700 transition"
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div>
                            <span className="text-xs font-mono text-indigo-400 block mb-0.5">
                              {app.scheme_code}
                            </span>
                            <h4 className="text-base font-bold text-white">{app.scheme_name}</h4>
                            <p className="text-xs text-slate-400 mt-0.5">{app.ministry}</p>
                          </div>
                          <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${badge.bg}`}>
                            {badge.label}
                          </span>
                        </div>

                        <div className="flex items-center justify-between text-xs text-slate-400 border-t border-slate-800 pt-3">
                          <div>
                            Match Score: <span className="text-emerald-400 font-bold">{app.match_score}%</span>
                          </div>
                          {app.max_subsidy_amount && (
                            <div>
                              Max Subsidy: <span className="text-white font-semibold">{formatINR(app.max_subsidy_amount)}</span>
                            </div>
                          )}
                        </div>

                        {app.application_reference_number && (
                          <div className="text-xs text-slate-300 bg-slate-950/60 p-2 rounded-lg border border-slate-800 font-mono">
                            Ref No: {app.application_reference_number}
                          </div>
                        )}

                        {app.notes && (
                          <p className="text-xs text-slate-400 italic bg-slate-950/40 p-2.5 rounded-lg border border-slate-800/80">
                            &ldquo;{app.notes}&rdquo;
                          </p>
                        )}

                        <div className="flex items-center gap-2 pt-1">
                          <button
                            onClick={() => {
                              const found = summary?.schemes.find((s) => s.scheme_id === app.scheme_id);
                              if (found) openSchemeModal(found, "GUIDANCE");
                            }}
                            className="w-full py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg transition"
                          >
                            Update Progress & Notes
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Scheme Cards Grid */}
          {!loading && activeTab !== "TRACKED" && (
            <div className="space-y-4">
              {filteredSchemes.length === 0 ? (
                <div className="p-12 text-center bg-slate-900/40 border border-slate-800 rounded-2xl">
                  <h3 className="text-base font-bold text-white">No Schemes Found</h3>
                  <p className="text-xs text-slate-400 mt-1">Try resetting your search query or switching categories.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                  {filteredSchemes.map((scheme) => {
                    const typeBadge = getSchemeTypeBadge(scheme.scheme_type);
                    const isTracked = trackedApplications.some((a) => a.scheme_id === scheme.scheme_id);

                    return (
                      <div
                        key={scheme.scheme_id}
                        className={`p-6 bg-slate-900/90 border rounded-2xl flex flex-col justify-between transition group shadow-lg ${
                          scheme.is_eligible
                            ? "border-slate-800 hover:border-indigo-500/50"
                            : "border-slate-800/70 opacity-80 hover:opacity-100"
                        }`}
                      >
                        <div className="space-y-4">
                          {/* Top row: Type Badge, Ministry, Match Pill */}
                          <div className="flex items-start justify-between gap-3">
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${typeBadge.bg} ${typeBadge.text} ${typeBadge.border}`}
                              >
                                {getSchemeTypeLabel(scheme.scheme_type)}
                              </span>
                              <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">
                                {scheme.level}
                              </span>
                              {isTracked && (
                                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                  Tracked
                                </span>
                              )}
                            </div>

                            {/* Match Score Indicator */}
                            <div className="flex items-center gap-1.5">
                              <div
                                className={`px-2.5 py-1 rounded-lg text-xs font-bold border flex items-center gap-1 ${
                                  scheme.match_score >= 80
                                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                                    : scheme.match_score >= 50
                                    ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
                                    : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                                }`}
                              >
                                <span>{scheme.match_score}%</span>
                                <span className="text-[10px] font-normal">
                                  {scheme.is_eligible ? "Eligible" : "Ineligible"}
                                </span>
                              </div>
                            </div>
                          </div>

                          {/* Title & Ministry */}
                          <div>
                            <h3 className="text-lg font-bold text-white group-hover:text-indigo-300 transition">
                              {scheme.scheme_name}
                            </h3>
                            <p className="text-xs text-slate-400 mt-1">
                              {scheme.ministry} • <span className="text-slate-300">{scheme.nodal_agency}</span>
                            </p>
                          </div>

                          {/* Financial Benefit Banner */}
                          <div className="p-3.5 bg-slate-950/70 border border-slate-800/90 rounded-xl flex items-center justify-between">
                            <div>
                              <span className="text-[11px] text-slate-400 block font-medium">Estimated Financial Assistance</span>
                              <span className="text-base font-extrabold text-emerald-400">
                                {formatINR(scheme.estimated_subsidy_amount || scheme.max_subsidy_amount)}
                              </span>
                            </div>
                            {scheme.subsidy_percentage && (
                              <div className="text-right">
                                <span className="text-[11px] text-slate-400 block font-medium">Subsidy Rate</span>
                                <span className="text-sm font-bold text-slate-200">
                                  {scheme.subsidy_percentage}% Project Cost
                                </span>
                              </div>
                            )}
                            {scheme.interest_subsidy_rate && (
                              <div className="text-right">
                                <span className="text-[11px] text-slate-400 block font-medium">Interest Subvention</span>
                                <span className="text-sm font-bold text-blue-400">
                                  {scheme.interest_subsidy_rate}% p.a.
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Criteria Match Pills */}
                          <div className="space-y-1.5">
                            <div className="flex flex-wrap gap-1.5">
                              {scheme.matching_criteria.slice(0, 3).map((crit, idx) => (
                                <span
                                  key={idx}
                                  className="text-[11px] px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 flex items-center gap-1"
                                >
                                  <svg className="w-3 h-3 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                  </svg>
                                  {crit}
                                </span>
                              ))}
                              {scheme.unmet_criteria.slice(0, 2).map((crit, idx) => (
                                <span
                                  key={idx}
                                  className="text-[11px] px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20 flex items-center gap-1"
                                >
                                  <svg className="w-3 h-3 text-amber-400" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                                  </svg>
                                  {crit}
                                </span>
                              ))}
                            </div>
                          </div>
                        </div>

                        {/* Bottom Actions */}
                        <div className="flex items-center gap-2.5 pt-5 border-t border-slate-800/80 mt-4">
                          <button
                            onClick={() => openSchemeModal(scheme, "CRITERIA")}
                            className="flex-1 py-2 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 text-xs font-semibold rounded-xl border border-indigo-500/30 transition text-center"
                          >
                            Criterion Audit
                          </button>
                          <button
                            onClick={() => openSchemeModal(scheme, "DOCUMENTS")}
                            className="flex-1 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition text-center"
                          >
                            Document Vault
                          </button>
                          <button
                            onClick={() => openSchemeModal(scheme, "GUIDANCE")}
                            className="px-3.5 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-xl shadow-md transition"
                            title="Application Guidance & Tracker"
                          >
                            Apply
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* =================================================================== */}
          {/* Detailed Modal: Eligibility Breakdown, Gap Analysis & Guidance     */}
          {/* =================================================================== */}
          {selectedScheme && (
            <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
                {/* Modal Header */}
                <div className="p-6 bg-slate-950/80 border-b border-slate-800 flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-indigo-400">{selectedScheme.scheme_code}</span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-full font-bold border ${
                          selectedScheme.is_eligible
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                            : "bg-rose-500/10 text-rose-400 border-rose-500/30"
                        }`}
                      >
                        {selectedScheme.match_score}% Match • {selectedScheme.is_eligible ? "Eligible" : "Needs Remediation"}
                      </span>
                    </div>
                    <h2 className="text-xl font-bold text-white mt-1">{selectedScheme.scheme_name}</h2>
                    <p className="text-xs text-slate-400 mt-0.5">{selectedScheme.ministry}</p>
                  </div>
                  <button
                    onClick={() => setSelectedScheme(null)}
                    className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Modal Tab Buttons */}
                <div className="flex border-b border-slate-800 bg-slate-900 px-6 gap-6 text-sm">
                  <button
                    onClick={() => setModalTab("CRITERIA")}
                    className={`py-3 font-semibold border-b-2 transition ${
                      modalTab === "CRITERIA"
                        ? "text-indigo-400 border-indigo-500"
                        : "text-slate-400 border-transparent hover:text-slate-200"
                    }`}
                  >
                    Eligibility Audit (Fragment 109)
                  </button>
                  <button
                    onClick={() => setModalTab("DOCUMENTS")}
                    className={`py-3 font-semibold border-b-2 transition ${
                      modalTab === "DOCUMENTS"
                        ? "text-indigo-400 border-indigo-500"
                        : "text-slate-400 border-transparent hover:text-slate-200"
                    }`}
                  >
                    Document Vault Readiness (Fragment 110)
                  </button>
                  <button
                    onClick={() => setModalTab("GUIDANCE")}
                    className={`py-3 font-semibold border-b-2 transition ${
                      modalTab === "GUIDANCE"
                        ? "text-indigo-400 border-indigo-500"
                        : "text-slate-400 border-transparent hover:text-slate-200"
                    }`}
                  >
                    Application Roadmap (Fragment 111)
                  </button>
                </div>

                {/* Modal Body */}
                <div className="p-6 overflow-y-auto space-y-6 flex-1">
                  {modalLoading && (
                    <div className="text-center py-10">
                      <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                      <p className="text-xs text-slate-400">Auditing document vault and statutory criteria...</p>
                    </div>
                  )}

                  {/* TAB 1: Eligibility Audit (Fragment 109) */}
                  {!modalLoading && modalTab === "CRITERIA" && (
                    <div className="space-y-4">
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800">
                        <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-2">
                          Recommendations & Next Actions
                        </h4>
                        <ul className="space-y-1 text-xs text-slate-300">
                          {selectedScheme.recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start gap-2">
                              <span className="text-indigo-400 mt-0.5">•</span>
                              <span>{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      <div className="space-y-2">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                          Statutory Criterion Evaluation Breakdown
                        </h4>
                        <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
                          {selectedScheme.criteria_breakdown.map((crit, idx) => (
                            <div key={idx} className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
                              <div className="space-y-1">
                                <div className="flex items-center gap-2">
                                  <span className="font-semibold text-white">{crit.name}</span>
                                  {crit.is_hard_criterion && (
                                    <span className="text-[10px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded">
                                      Mandatory
                                    </span>
                                  )}
                                </div>
                                <p className="text-slate-400">{crit.explanation}</p>
                                <div className="text-[11px] text-slate-500 flex gap-4">
                                  <span>Required: <strong className="text-slate-300">{crit.required_val}</strong></span>
                                  <span>Actual: <strong className="text-slate-300">{crit.actual_val}</strong></span>
                                </div>
                              </div>
                              <div>
                                <span
                                  className={`px-2.5 py-1 rounded-md font-bold text-[11px] ${
                                    crit.status === "PASS"
                                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                      : crit.status === "WARNING"
                                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                      : crit.status === "FAIL"
                                      ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                      : "bg-slate-800 text-slate-400"
                                  }`}
                                >
                                  {crit.status}
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 2: Document Vault Gap Analysis (Fragment 110) */}
                  {!modalLoading && modalTab === "DOCUMENTS" && (
                    <div className="space-y-4">
                      {/* Readiness Progress Bar */}
                      <div className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-bold text-white">Vault Document Readiness</span>
                          <span className="font-extrabold text-indigo-400">
                            {selectedScheme.document_readiness?.readiness_percentage ?? 0}%
                          </span>
                        </div>
                        <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                          <div
                            className="bg-gradient-to-r from-indigo-500 to-emerald-500 h-full transition-all duration-500"
                            style={{ width: `${selectedScheme.document_readiness?.readiness_percentage ?? 0}%` }}
                          />
                        </div>
                        <div className="text-[11px] text-slate-400 flex justify-between">
                          <span>
                            {selectedScheme.document_readiness?.total_available ?? 0} of{" "}
                            {selectedScheme.document_readiness?.total_required ?? selectedScheme.required_document_codes.length} verified in Document Vault
                          </span>
                          <Link href="/documents" className="text-indigo-400 hover:underline">
                            Upload missing files →
                          </Link>
                        </div>
                      </div>

                      {/* Checklist */}
                      <div className="space-y-2">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                          Required Documents Checklist
                        </h4>
                        <div className="divide-y divide-slate-800 border border-slate-800 rounded-xl overflow-hidden bg-slate-950/40">
                          {(selectedScheme.document_readiness?.documents || selectedScheme.required_document_codes.map((code) => ({
                            code,
                            title: code.replace(/_/g, " "),
                            is_available: false,
                            is_verified: false,
                          }))).map((doc, idx) => (
                            <div key={idx} className="p-3.5 flex items-center justify-between gap-3 text-xs">
                              <div className="flex items-center gap-3">
                                <div
                                  className={`w-6 h-6 rounded-full flex items-center justify-center ${
                                    doc.is_available
                                      ? "bg-emerald-500/20 text-emerald-400"
                                      : "bg-rose-500/20 text-rose-400"
                                  }`}
                                >
                                  {doc.is_available ? (
                                    <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
                                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                    </svg>
                                  ) : (
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                                    </svg>
                                  )}
                                </div>
                                <div>
                                  <span className="font-semibold text-white block">{doc.title}</span>
                                  <span className="text-[11px] font-mono text-slate-500">{doc.code}</span>
                                </div>
                              </div>

                              <div>
                                {doc.is_available ? (
                                  <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                                    {doc.is_verified ? "Verified OCR" : "Uploaded"}
                                  </span>
                                ) : (
                                  <Link
                                    href="/documents"
                                    className="text-[11px] font-semibold text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 px-2 py-1 rounded border border-indigo-500/30 transition"
                                  >
                                    Upload Now
                                  </Link>
                                )}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* TAB 3: Application Roadmap & Tracker (Fragment 111) */}
                  {!modalLoading && modalTab === "GUIDANCE" && (
                    <div className="space-y-6">
                      {/* Step-by-Step Guidance */}
                      <div className="space-y-3">
                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                          Standard Operating Procedure (SOP) Roadmap
                        </h4>
                        <div className="space-y-2.5">
                          {selectedScheme.guidance_steps.map((step) => (
                            <div
                              key={step.step}
                              className="p-3.5 bg-slate-950/60 rounded-xl border border-slate-800 flex items-start gap-3 text-xs"
                            >
                              <div className="w-6 h-6 rounded-full bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 font-bold flex items-center justify-center flex-shrink-0">
                                {step.step}
                              </div>
                              <div className="space-y-0.5">
                                <h5 className="font-bold text-white">{step.title}</h5>
                                <p className="text-slate-400 leading-relaxed">{step.instruction}</p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Official Portal External Link */}
                      {selectedScheme.official_portal_url && (
                        <div className="p-4 bg-gradient-to-r from-blue-950/40 to-indigo-950/40 rounded-xl border border-blue-500/30 flex items-center justify-between gap-4">
                          <div>
                            <span className="text-xs font-bold text-white block">Official Nodal Portal</span>
                            <span className="text-xs text-slate-400">
                              Submit applications and project reports directly on the designated government system.
                            </span>
                          </div>
                          <a
                            href={selectedScheme.official_portal_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold rounded-xl shadow-md transition flex items-center gap-1.5 flex-shrink-0"
                          >
                            <span>Open Portal</span>
                            <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </a>
                        </div>
                      )}

                      {/* Scheme Tracking Form */}
                      <div className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 space-y-3">
                        <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider">
                          Internal Application Milestone Tracker
                        </h4>

                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                          <div>
                            <label className="block text-slate-400 mb-1 font-medium">Milestone Stage</label>
                            <select
                              value={trackingStatus}
                              onChange={(e) => setTrackingStatus(e.target.value as SchemeApplicationStatus)}
                              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 focus:outline-none focus:border-indigo-500"
                            >
                              <option value="BOOKMARKED">Bookmarked for Scrutiny</option>
                              <option value="PREPARING">DPR In Preparation</option>
                              <option value="APPLIED">Applied Online / Physical Form Filed</option>
                              <option value="UNDER_SCRUTINY">Under Agency Scrutiny</option>
                              <option value="SANCTIONED">Sanction Letter Issued</option>
                              <option value="DISBURSED">Subsidy Disbursed</option>
                              <option value="REJECTED">Rejected</option>
                            </select>
                          </div>

                          <div>
                            <label className="block text-slate-400 mb-1 font-medium">
                              Application Reference / Ack Number
                            </label>
                            <input
                              type="text"
                              value={trackingRef}
                              onChange={(e) => setTrackingRef(e.target.value)}
                              placeholder="e.g. KVIC/2026/MH/88921"
                              className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                            />
                          </div>
                        </div>

                        <div>
                          <label className="block text-slate-400 mb-1 text-xs font-medium">
                            Internal Project Notes & Target Milestones
                          </label>
                          <textarea
                            value={trackingNotes}
                            onChange={(e) => setTrackingNotes(e.target.value)}
                            rows={2}
                            placeholder="Add CA net worth figures, bank loan sanction status, or DPR draft notes..."
                            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                          />
                        </div>

                        {saveSuccessMsg && (
                          <div className="p-2 text-xs bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-lg">
                            {saveSuccessMsg}
                          </div>
                        )}

                        <div className="flex justify-end pt-1">
                          <button
                            onClick={handleSaveTracking}
                            disabled={isSavingTracking}
                            className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-lg shadow-md transition flex items-center gap-1.5"
                          >
                            {isSavingTracking ? "Updating..." : "Save Milestone"}
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Modal Footer */}
                <div className="p-4 bg-slate-950/90 border-t border-slate-800 flex justify-end">
                  <button
                    onClick={() => setSelectedScheme(null)}
                    className="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl transition"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}

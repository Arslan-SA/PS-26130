"use client";

/**
 * DocumentHealthWidget — Document health summary card (Fragment 73 — UI).
 *
 * Displays:
 * - Health grade badge (A/B/C/D/F) with color coding
 * - Completeness score radial indicator
 * - Status breakdown (Verified / Pending / Flagged / Rejected)
 * - Expiry risk alerts (CRITICAL / HIGH)
 * - Deficiency list
 */

import React, { useEffect, useState } from "react";

interface ExpiryRiskItem {
  document_id: string;
  file_name: string;
  document_type: string;
  expiry_date: string | null;
  days_remaining: number | null;
  severity: "NONE" | "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

interface DeficiencyItem {
  document_id: string;
  file_name: string;
  document_type: string;
  notes: string;
}

interface DocumentHealthReport {
  business_id: string;
  total_documents: number;
  verified_count: number;
  pending_count: number;
  flagged_count: number;
  rejected_count: number;
  completeness_score: number;
  expiry_risks: ExpiryRiskItem[];
  deficiencies: DeficiencyItem[];
  missing_requirement_types: string[];
  health_grade: "A" | "B" | "C" | "D" | "F";
}

interface Props {
  businessId: string;
}

const GRADE_CONFIG = {
  A: { label: "Excellent", className: "text-emerald-400 border-emerald-500/40 bg-emerald-500/10" },
  B: { label: "Good", className: "text-blue-400 border-blue-500/40 bg-blue-500/10" },
  C: { label: "Fair", className: "text-amber-400 border-amber-500/40 bg-amber-500/10" },
  D: { label: "Poor", className: "text-orange-400 border-orange-500/40 bg-orange-500/10" },
  F: { label: "Critical", className: "text-rose-400 border-rose-500/40 bg-rose-500/10" },
};

const SEVERITY_CONFIG = {
  CRITICAL: "text-rose-400 bg-rose-500/10 border-rose-500/30",
  HIGH: "text-orange-400 bg-orange-500/10 border-orange-500/30",
  MEDIUM: "text-amber-400 bg-amber-500/10 border-amber-500/30",
  LOW: "text-blue-400 bg-blue-500/10 border-blue-500/30",
  NONE: "text-slate-400 bg-slate-700/40 border-slate-600/30",
};

async function fetchHealthReport(businessId: string): Promise<DocumentHealthReport> {
  const token = typeof window !== "undefined" ? localStorage.getItem("access_token") : null;
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  const res = await fetch(`${base}/documents/business/${businessId}/health`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error("Failed to load health report");
  return res.json();
}

export default function DocumentHealthWidget({ businessId }: Props) {
  const [report, setReport] = useState<DocumentHealthReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchHealthReport(businessId)
      .then(setReport)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [businessId]);

  if (loading) {
    return (
      <div className="p-6 bg-slate-900/80 border border-slate-800 rounded-2xl flex items-center gap-3">
        <div className="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
        <span className="text-sm text-slate-400">Loading document health…</span>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="p-6 bg-slate-900/80 border border-rose-500/20 rounded-2xl">
        <p className="text-sm text-rose-400">⚠ Could not load document health report</p>
      </div>
    );
  }

  const grade = report.health_grade as keyof typeof GRADE_CONFIG;
  const gradeCfg = GRADE_CONFIG[grade] || GRADE_CONFIG.F;
  const urgentRisks = report.expiry_risks.filter(
    (r) => r.severity === "CRITICAL" || r.severity === "HIGH"
  );

  // Circumference for the score ring
  const radius = 36;
  const circ = 2 * Math.PI * radius;
  const dash = circ * (report.completeness_score / 100);

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">📊 Document Health</h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {report.total_documents} document{report.total_documents !== 1 ? "s" : ""} on file
          </p>
        </div>
        {/* Health Grade Badge */}
        <div
          className={`flex flex-col items-center justify-center w-14 h-14 rounded-xl border-2 font-bold text-xl ${gradeCfg.className}`}
        >
          {grade}
          <span className="text-[9px] font-normal mt-0.5">{gradeCfg.label}</span>
        </div>
      </div>

      <div className="p-5 space-y-5">
        {/* Score + Status Row */}
        <div className="flex items-center gap-6">
          {/* Radial Score */}
          <div className="relative flex-shrink-0">
            <svg width="88" height="88" className="-rotate-90">
              <circle cx="44" cy="44" r={radius} fill="none" stroke="#1e293b" strokeWidth="8" />
              <circle
                cx="44"
                cy="44"
                r={radius}
                fill="none"
                stroke={
                  report.completeness_score >= 85 ? "#10b981"
                  : report.completeness_score >= 70 ? "#3b82f6"
                  : report.completeness_score >= 55 ? "#f59e0b"
                  : "#f43f5e"
                }
                strokeWidth="8"
                strokeLinecap="round"
                strokeDasharray={`${dash} ${circ}`}
                style={{ transition: "stroke-dasharray 1s ease" }}
              />
            </svg>
            <div className="absolute inset-0 flex flex-col items-center justify-center">
              <span className="text-base font-bold text-slate-100">
                {report.completeness_score.toFixed(0)}%
              </span>
              <span className="text-[9px] text-slate-500">Score</span>
            </div>
          </div>

          {/* Status breakdown */}
          <div className="flex-1 grid grid-cols-2 gap-2">
            {[
              { label: "Verified", value: report.verified_count, color: "text-emerald-400" },
              { label: "Pending", value: report.pending_count, color: "text-amber-400" },
              { label: "Flagged", value: report.flagged_count, color: "text-orange-400" },
              { label: "Rejected", value: report.rejected_count, color: "text-rose-400" },
            ].map((s) => (
              <div key={s.label} className="flex items-baseline gap-1.5">
                <span className={`text-lg font-bold ${s.color}`}>{s.value}</span>
                <span className="text-xs text-slate-500">{s.label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Urgent Expiry Risks */}
        {urgentRisks.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              ⏳ Expiry Alerts
            </p>
            {urgentRisks.slice(0, 3).map((r) => (
              <div
                key={r.document_id}
                className={`flex items-center justify-between px-3 py-2 rounded-lg border text-xs ${
                  SEVERITY_CONFIG[r.severity]
                }`}
              >
                <span className="truncate max-w-[60%]">{r.file_name}</span>
                <span className="font-semibold flex-shrink-0">
                  {r.days_remaining !== null && r.days_remaining < 0
                    ? "Expired"
                    : r.days_remaining !== null
                    ? `${r.days_remaining}d left`
                    : "—"}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Deficiency Notices */}
        {report.deficiencies.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              ⚠ Deficiency Notices
            </p>
            {report.deficiencies.slice(0, 2).map((d) => (
              <div
                key={d.document_id}
                className="px-3 py-2 rounded-lg border border-rose-500/20 bg-rose-500/5 text-xs text-rose-300"
              >
                <p className="font-medium text-rose-400 truncate">{d.file_name}</p>
                <p className="text-rose-300/70 mt-0.5 line-clamp-2">{d.notes}</p>
              </div>
            ))}
          </div>
        )}

        {/* All clear */}
        {urgentRisks.length === 0 && report.deficiencies.length === 0 && (
          <div className="flex items-center gap-2 px-3 py-2.5 bg-emerald-500/5 border border-emerald-500/20 rounded-lg">
            <span className="text-emerald-400 text-base">✓</span>
            <span className="text-xs text-emerald-300">
              No expiry risks or deficiencies detected
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

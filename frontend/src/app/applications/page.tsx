"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ApplicationStatus,
  ApplicationSummary,
  getApplications,
} from "@/lib/applications";
import { useAuth } from "@/components/auth/AuthProvider";

export default function ApplicationsPage() {
  const { user } = useAuth();
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [filteredApps, setFilteredApps] = useState<ApplicationSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        setError(null);
        const data = await getApplications();
        setApplications(data);
        setFilteredApps(data);
      } catch (err: any) {
        console.error("Failed to load applications:", err);
        setError(err.message || "Failed to load statutory applications.");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, []);

  const handleFilterChange = (filter: string) => {
    setSelectedFilter(filter);
    if (filter === "ALL") {
      setFilteredApps(applications);
    } else if (filter === "ACTIVE") {
      setFilteredApps(
        applications.filter((a) =>
          ["SUBMITTED", "UNDER_REVIEW", "RESUBMITTED", "INSPECTION_SCHEDULED", "INSPECTION_COMPLETED"].includes(
            a.status
          )
        )
      );
    } else if (filter === "QUERIES") {
      setFilteredApps(applications.filter((a) => a.status === "QUERY_RAISED"));
    } else if (filter === "APPROVED") {
      setFilteredApps(applications.filter((a) => a.status === "APPROVED"));
    } else if (filter === "REJECTED") {
      setFilteredApps(applications.filter((a) => a.status === "REJECTED"));
    }
  };

  const getStatusBadge = (status: ApplicationStatus) => {
    switch (status) {
      case "DRAFT":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-100 text-slate-700 border border-slate-300">
            Draft
          </span>
        );
      case "SUBMITTED":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800 border border-blue-200">
            Submitted
          </span>
        );
      case "UNDER_REVIEW":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-800 border border-amber-200 animate-pulse">
            Under Scrutiny
          </span>
        );
      case "QUERY_RAISED":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-100 text-rose-800 border border-rose-300">
            Deficiency / Action Needed
          </span>
        );
      case "RESUBMITTED":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-800 border border-purple-200">
            Resubmitted
          </span>
        );
      case "INSPECTION_SCHEDULED":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-cyan-100 text-cyan-800 border border-cyan-200">
            Inspection Scheduled
          </span>
        );
      case "INSPECTION_COMPLETED":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-indigo-100 text-indigo-800 border border-indigo-200">
            Inspection Done
          </span>
        );
      case "APPROVED":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
            Clearance Granted
          </span>
        );
      case "REJECTED":
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800 border border-red-300">
            Rejected
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-slate-100 text-slate-700">
            {status}
          </span>
        );
    }
  };

  const totalCount = applications.length;
  const underReviewCount = applications.filter((a) =>
    ["SUBMITTED", "UNDER_REVIEW", "RESUBMITTED", "INSPECTION_SCHEDULED", "INSPECTION_COMPLETED"].includes(a.status)
  ).length;
  const queryCount = applications.filter((a) => a.status === "QUERY_RAISED").length;
  const approvedCount = applications.filter((a) => a.status === "APPROVED").length;

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Breadcrumb & Navigation */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <nav className="text-xs text-slate-500 mb-1 flex items-center space-x-1.5">
              <Link href="/dashboard" className="hover:text-gov-blue">Dashboard</Link>
              <span>/</span>
              <span className="text-slate-800 font-semibold">Statutory Applications</span>
            </nav>
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Regulatory Clearances & Submissions
            </h1>
            <p className="text-sm text-slate-600">
              Single-window statutory filing tracking across State Pollution Boards, Fire Services, DISH, and DISCOMs.
            </p>
          </div>
          <div className="flex items-center space-x-3">
            <Link
              href="/approvals"
              className="px-4 py-2 border border-slate-300 rounded-md text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 shadow-sm"
            >
              Approval Navigator
            </Link>
            <Link
              href="/approvals"
              className="px-4 py-2 bg-gov-blue text-white rounded-md text-sm font-semibold hover:bg-slate-800 shadow-sm flex items-center space-x-2"
            >
              <span>+ New Clearance Filing</span>
            </Link>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
            <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total Filings</div>
            <div className="mt-1 text-2xl font-bold text-slate-900">{totalCount}</div>
            <div className="mt-1 text-xs text-slate-500">Across all authorities</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-amber-200 shadow-sm bg-gradient-to-br from-white to-amber-50/30">
            <div className="text-xs font-medium text-amber-700 uppercase tracking-wider">In Scrutiny</div>
            <div className="mt-1 text-2xl font-bold text-amber-900">{underReviewCount}</div>
            <div className="mt-1 text-xs text-amber-600">Department review active</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-rose-200 shadow-sm bg-gradient-to-br from-white to-rose-50/30">
            <div className="text-xs font-medium text-rose-700 uppercase tracking-wider">Action Needed</div>
            <div className="mt-1 text-2xl font-bold text-rose-900">{queryCount}</div>
            <div className="mt-1 text-xs text-rose-600">Deficiencies to rectify</div>
          </div>
          <div className="bg-white p-4 rounded-lg border border-emerald-200 shadow-sm bg-gradient-to-br from-white to-emerald-50/30">
            <div className="text-xs font-medium text-emerald-700 uppercase tracking-wider">Granted NOCs</div>
            <div className="mt-1 text-2xl font-bold text-emerald-900">{approvedCount}</div>
            <div className="mt-1 text-xs text-emerald-600">Certificates available</div>
          </div>
        </div>

        {/* Query Alert Notice if any */}
        {queryCount > 0 && (
          <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <span className="text-xl">⚠️</span>
              <div>
                <h4 className="text-sm font-semibold text-rose-900">
                  {queryCount} Statutory Deficiency {queryCount === 1 ? "Query Requires" : "Queries Require"} Your Response
                </h4>
                <p className="text-xs text-rose-700">
                  Government scrutiny officers have flagged clarification items on your filings. Respond promptly to prevent SLA pauses.
                </p>
              </div>
            </div>
            <button
              onClick={() => handleFilterChange("QUERIES")}
              className="px-3 py-1.5 bg-rose-600 text-white rounded text-xs font-medium hover:bg-rose-700 shadow-sm"
            >
              View Queries
            </button>
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
          {[
            { id: "ALL", label: `All Filings (${totalCount})` },
            { id: "ACTIVE", label: `In Scrutiny (${underReviewCount})` },
            { id: "QUERIES", label: `Action Needed (${queryCount})` },
            { id: "APPROVED", label: `Approved (${approvedCount})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => handleFilterChange(tab.id)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                selectedFilter === tab.id
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Applications List */}
        {isLoading ? (
          <div className="p-12 text-center bg-white rounded-lg border border-slate-200">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gov-blue"></div>
            <p className="mt-3 text-sm text-slate-500">Loading statutory applications queue...</p>
          </div>
        ) : error ? (
          <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
            {error}
          </div>
        ) : filteredApps.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-lg border border-slate-200 shadow-sm">
            <span className="text-4xl">📋</span>
            <h3 className="mt-3 text-base font-semibold text-slate-900">No applications match this filter</h3>
            <p className="mt-1 text-sm text-slate-500 max-w-sm mx-auto">
              Initiate statutory clearances via the AI Approval Navigator to start your enterprise compliance pipeline.
            </p>
            <div className="mt-4">
              <Link
                href="/approvals"
                className="px-4 py-2 bg-gov-blue text-white rounded-md text-xs font-semibold hover:bg-slate-800"
              >
                Go to Approval Navigator
              </Link>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {filteredApps.map((app) => (
              <div
                key={app.id}
                className="bg-white rounded-lg border border-slate-200 shadow-sm hover:shadow transition-shadow p-5 flex flex-col md:flex-row md:items-center md:justify-between gap-4"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex items-center space-x-2.5">
                    <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                      {app.application_number}
                    </span>
                    <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                      Dept: <strong className="text-slate-700">{app.department_code}</strong>
                    </span>
                    {getStatusBadge(app.status)}
                  </div>

                  <div>
                    <h3 className="text-base font-semibold text-slate-900">
                      {app.approval_title || app.approval_code}
                    </h3>
                    <p className="text-xs text-slate-500">
                      Enterprise: {app.business_name || "Primary Manufacturing Unit"} • Fee: ₹
                      {app.fee_amount.toLocaleString("en-IN")}{" "}
                      {app.fee_paid ? (
                        <span className="text-emerald-600 font-medium">✓ Paid</span>
                      ) : (
                        <span className="text-amber-600 font-medium">⚠ Fee Pending</span>
                      )}
                    </p>
                  </div>

                  {app.sla_days_remaining !== null && app.sla_days_remaining !== undefined && (
                    <div className="flex items-center space-x-2 text-xs">
                      <span className="text-slate-500">Public Service SLA:</span>
                      <span
                        className={`font-semibold ${
                          app.sla_days_remaining <= 3 ? "text-rose-600 font-bold" : "text-slate-700"
                        }`}
                      >
                        {app.sla_days_remaining} days remaining
                      </span>
                    </div>
                  )}

                  {app.approval_certificate_number && (
                    <div className="text-xs text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded inline-block font-mono border border-emerald-200">
                      Clearance License: <strong>{app.approval_certificate_number}</strong>
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-3 self-end md:self-center">
                  {app.status === "QUERY_RAISED" ? (
                    <Link
                      href={`/applications/${app.id}`}
                      className="px-4 py-2 bg-rose-600 text-white rounded-md text-xs font-semibold hover:bg-rose-700 shadow-sm"
                    >
                      Respond to Query →
                    </Link>
                  ) : app.status === "APPROVED" ? (
                    <Link
                      href={`/applications/${app.id}`}
                      className="px-4 py-2 bg-emerald-600 text-white rounded-md text-xs font-semibold hover:bg-emerald-700 shadow-sm"
                    >
                      View Certificate
                    </Link>
                  ) : (
                    <Link
                      href={`/applications/${app.id}`}
                      className="px-4 py-2 border border-slate-300 text-slate-700 rounded-md text-xs font-medium hover:bg-slate-50 shadow-sm"
                    >
                      Track Scrutiny
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

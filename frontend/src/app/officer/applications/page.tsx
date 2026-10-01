"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  ApplicationStatus,
  ApplicationSummary,
  OfficerInboxSummary,
  determineApplication,
  getOfficerApplications,
  getOfficerInboxSummary,
  raiseOfficerQuery,
  scheduleInspection,
  startOfficerReview,
} from "@/lib/applications";
import { useAuth } from "@/components/auth/AuthProvider";

export default function OfficerApplicationsPage() {
  const { user } = useAuth();
  const [inboxSummary, setInboxSummary] = useState<OfficerInboxSummary | null>(null);
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [filteredApps, setFilteredApps] = useState<ApplicationSummary[]>([]);
  const [selectedTab, setSelectedTab] = useState<string>("PENDING");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals state
  const [activeModal, setActiveModal] = useState<"QUERY" | "INSPECTION" | "DETERMINE" | null>(null);
  const [selectedApp, setSelectedApp] = useState<ApplicationSummary | null>(null);

  // Form states
  const [queryTitle, setQueryTitle] = useState("");
  const [queryText, setQueryText] = useState("");

  const [inspectorId, setInspectorId] = useState("");
  const [inspectDate, setInspectDate] = useState("");
  const [inspectInstructions, setInspectInstructions] = useState("");

  const [decision, setDecision] = useState<"APPROVED" | "REJECTED">("APPROVED");
  const [decisionRemarks, setDecisionRemarks] = useState("");
  const [rejectionReason, setRejectionReason] = useState("");
  const [validityYears, setValidityYears] = useState(5);

  const [isProcessing, setIsProcessing] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const loadAllData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const [inbox, apps] = await Promise.all([
        getOfficerInboxSummary(),
        getOfficerApplications(),
      ]);
      setInboxSummary(inbox);
      setApplications(apps);
      filterList(selectedTab, apps);
    } catch (err: any) {
      console.error("Failed to load officer dashboard:", err);
      setError(err.message || "Failed to load scrutiny queue.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const filterList = (tab: string, items: ApplicationSummary[]) => {
    setSelectedTab(tab);
    if (tab === "PENDING") {
      setFilteredApps(items.filter((a) => ["SUBMITTED", "RESUBMITTED"].includes(a.status)));
    } else if (tab === "UNDER_REVIEW") {
      setFilteredApps(items.filter((a) => a.status === "UNDER_REVIEW"));
    } else if (tab === "QUERIES") {
      setFilteredApps(items.filter((a) => a.status === "QUERY_RAISED"));
    } else if (tab === "INSPECTIONS") {
      setFilteredApps(
        items.filter((a) => ["INSPECTION_SCHEDULED", "INSPECTION_COMPLETED"].includes(a.status))
      );
    } else if (tab === "DECIDED") {
      setFilteredApps(items.filter((a) => ["APPROVED", "REJECTED"].includes(a.status)));
    } else {
      setFilteredApps(items);
    }
  };

  const handleStartReview = async (app: ApplicationSummary) => {
    try {
      setIsProcessing(true);
      await startOfficerReview(app.id);
      setSuccessMsg(`Commenced scrutiny on ${app.application_number}`);
      await loadAllData();
    } catch (err: any) {
      alert(err.message || "Failed to commence scrutiny.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleRaiseQuery = async () => {
    if (!selectedApp) return;
    if (!queryTitle.trim() || !queryText.trim()) {
      alert("Please provide both a title and deficiency description.");
      return;
    }
    try {
      setIsProcessing(true);
      await raiseOfficerQuery(selectedApp.id, {
        query_title: queryTitle,
        query_text: queryText,
      });
      setActiveModal(null);
      setQueryTitle("");
      setQueryText("");
      setSuccessMsg(`Deficiency notice issued on ${selectedApp.application_number}`);
      await loadAllData();
    } catch (err: any) {
      alert(err.message || "Failed to raise query.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleScheduleInspection = async () => {
    if (!selectedApp) return;
    if (!inspectorId.trim() || !inspectDate) {
      alert("Please specify inspector and scheduled date.");
      return;
    }
    try {
      setIsProcessing(true);
      await scheduleInspection(selectedApp.id, {
        inspector_id: inspectorId,
        scheduled_date: new Date(inspectDate).toISOString(),
        instructions: inspectInstructions || undefined,
      });
      setActiveModal(null);
      setInspectDate("");
      setInspectInstructions("");
      setSuccessMsg(`Physical site inspection scheduled for ${selectedApp.application_number}`);
      await loadAllData();
    } catch (err: any) {
      alert(err.message || "Failed to schedule inspection.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDetermination = async () => {
    if (!selectedApp) return;
    if (decision === "REJECTED" && !rejectionReason.trim()) {
      alert("Statutory rejection reason must be provided.");
      return;
    }
    try {
      setIsProcessing(true);
      await determineApplication(selectedApp.id, {
        decision,
        remarks: decisionRemarks || undefined,
        rejection_reason: decision === "REJECTED" ? rejectionReason : undefined,
        validity_years: decision === "APPROVED" ? validityYears : undefined,
      });
      setActiveModal(null);
      setDecisionRemarks("");
      setRejectionReason("");
      setSuccessMsg(
        `Application ${selectedApp.application_number} ${decision === "APPROVED" ? "Granted" : "Rejected"}.`
      );
      await loadAllData();
    } catch (err: any) {
      alert(err.message || "Failed to record determination.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="text-xs font-semibold text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded inline-block">
              Department Scrutiny Portal
            </div>
            <h1 className="mt-2 text-2xl font-bold text-slate-900 tracking-tight">
              Regulatory Scrutiny & Approval Queue
            </h1>
            <p className="text-sm text-slate-600">
              Department: <strong>{inboxSummary?.department_code || user?.department_id || "Regulatory Board"}</strong> •
              Officer: <strong>{inboxSummary?.full_name || user?.full_name}</strong>
            </p>
          </div>
          <button
            onClick={loadAllData}
            className="px-4 py-2 bg-white border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-sm"
          >
            ↻ Refresh Queue
          </button>
        </div>

        {/* Success Alert */}
        {successMsg && (
          <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium">
            ✓ {successMsg}
          </div>
        )}

        {/* Live Metrics Grid */}
        {inboxSummary && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="bg-white p-4 rounded-lg border border-slate-200 shadow-sm">
              <div className="text-2xs font-medium text-slate-500 uppercase">Pending Review</div>
              <div className="mt-1 text-2xl font-bold text-slate-900">
                {inboxSummary.queue_metrics.pending_scrutiny}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-amber-200 shadow-sm bg-amber-50/20">
              <div className="text-2xs font-medium text-amber-700 uppercase">Under Scrutiny</div>
              <div className="mt-1 text-2xl font-bold text-amber-900">
                {inboxSummary.queue_metrics.under_review}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-rose-200 shadow-sm bg-rose-50/20">
              <div className="text-2xs font-medium text-rose-700 uppercase">Awaiting Applicant</div>
              <div className="mt-1 text-2xl font-bold text-rose-900">
                {inboxSummary.queue_metrics.queries_pending_applicant_response}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-cyan-200 shadow-sm bg-cyan-50/20">
              <div className="text-2xs font-medium text-cyan-700 uppercase">Site Visits</div>
              <div className="mt-1 text-2xl font-bold text-cyan-900">
                {inboxSummary.queue_metrics.inspections_scheduled}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-emerald-200 shadow-sm bg-emerald-50/20">
              <div className="text-2xs font-medium text-emerald-700 uppercase">Approved</div>
              <div className="mt-1 text-2xl font-bold text-emerald-900">
                {inboxSummary.queue_metrics.approved_count}
              </div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-indigo-200 shadow-sm bg-indigo-50/20">
              <div className="text-2xs font-medium text-indigo-700 uppercase">SLA Compliance</div>
              <div className="mt-1 text-2xl font-bold text-indigo-900">
                {inboxSummary.queue_metrics.sla_compliance_rate_percent}%
              </div>
            </div>
          </div>
        )}

        {/* Priority Guidance */}
        {inboxSummary && (
          <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-lg flex items-center justify-between text-xs text-blue-900">
            <div>
              <strong>Action Focus:</strong> {inboxSummary.next_action}
            </div>
            {inboxSummary.queue_metrics.sla_critical_count > 0 && (
              <span className="font-bold text-rose-600 bg-rose-100 px-2 py-0.5 rounded">
                ⚠️ {inboxSummary.queue_metrics.sla_critical_count} SLA Critical Filings
              </span>
            )}
          </div>
        )}

        {/* Filter Tabs */}
        <div className="flex items-center space-x-2 border-b border-slate-200 pb-2">
          {[
            { id: "PENDING", label: `Incoming Submissions (${inboxSummary?.queue_metrics.pending_scrutiny || 0})` },
            { id: "UNDER_REVIEW", label: `In Scrutiny (${inboxSummary?.queue_metrics.under_review || 0})` },
            { id: "QUERIES", label: `Deficiency Queries (${inboxSummary?.queue_metrics.queries_pending_applicant_response || 0})` },
            { id: "INSPECTIONS", label: `Inspections (${inboxSummary?.queue_metrics.inspections_scheduled || 0})` },
            { id: "DECIDED", label: "Finalized / Decided" },
            { id: "ALL", label: `All Filings (${applications.length})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => filterList(tab.id, applications)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                selectedTab === tab.id
                  ? "bg-slate-900 text-white"
                  : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Queue Items */}
        {isLoading ? (
          <div className="p-12 text-center bg-white rounded-lg border border-slate-200">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gov-blue"></div>
            <p className="mt-3 text-sm text-slate-500">Loading department applications...</p>
          </div>
        ) : error ? (
          <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
            {error}
          </div>
        ) : filteredApps.length === 0 ? (
          <div className="p-12 text-center bg-white rounded-lg border border-slate-200 shadow-sm">
            <span className="text-3xl">✓</span>
            <h3 className="mt-2 text-base font-semibold text-slate-900">Queue is clear</h3>
            <p className="text-xs text-slate-500 mt-1">No applications currently match this queue state.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredApps.map((app) => (
              <div
                key={app.id}
                className="bg-white rounded-lg border border-slate-200 shadow-sm p-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4"
              >
                <div className="space-y-1.5 flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                      {app.application_number}
                    </span>
                    <span className="text-xs font-medium text-slate-500 uppercase">
                      Dept: {app.department_code}
                    </span>
                    <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-700">
                      {app.status}
                    </span>
                    {app.sla_days_remaining != null && (
                      <span
                        className={`text-2xs font-bold px-2 py-0.5 rounded ${
                          app.sla_days_remaining <= 3
                            ? "bg-rose-100 text-rose-800"
                            : "bg-blue-50 text-blue-800"
                        }`}
                      >
                        SLA: {app.sla_days_remaining}d
                      </span>
                    )}
                  </div>

                  <h3 className="text-sm font-semibold text-slate-900">
                    {app.approval_title || app.approval_code}
                  </h3>
                  <p className="text-xs text-slate-500">
                    Enterprise: <strong>{app.business_name}</strong> • Fee: ₹{app.fee_amount.toLocaleString("en-IN")}{" "}
                    (Paid)
                  </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  {/* Action 1: Start Review if SUBMITTED or RESUBMITTED */}
                  {["SUBMITTED", "RESUBMITTED"].includes(app.status) && (
                    <button
                      onClick={() => handleStartReview(app)}
                      disabled={isProcessing}
                      className="px-3 py-1.5 bg-gov-blue text-white rounded text-xs font-semibold hover:bg-slate-800 shadow-sm"
                    >
                      Commence Scrutiny
                    </button>
                  )}

                  {/* Action 2: Raise Deficiency Query */}
                  {["SUBMITTED", "UNDER_REVIEW", "RESUBMITTED"].includes(app.status) && (
                    <button
                      onClick={() => {
                        setSelectedApp(app);
                        setActiveModal("QUERY");
                      }}
                      className="px-3 py-1.5 bg-rose-50 text-rose-700 border border-rose-200 rounded text-xs font-semibold hover:bg-rose-100"
                    >
                      Issue Deficiency Note
                    </button>
                  )}

                  {/* Action 3: Schedule Inspection */}
                  {["UNDER_REVIEW", "RESUBMITTED"].includes(app.status) && (
                    <button
                      onClick={() => {
                        setSelectedApp(app);
                        setActiveModal("INSPECTION");
                      }}
                      className="px-3 py-1.5 bg-cyan-50 text-cyan-800 border border-cyan-200 rounded text-xs font-semibold hover:bg-cyan-100"
                    >
                      Schedule Inspection
                    </button>
                  )}

                  {/* Action 4: Final Determination */}
                  {["UNDER_REVIEW", "INSPECTION_COMPLETED", "RESUBMITTED"].includes(app.status) && (
                    <button
                      onClick={() => {
                        setSelectedApp(app);
                        setActiveModal("DETERMINE");
                      }}
                      className="px-3 py-1.5 bg-emerald-600 text-white rounded text-xs font-semibold hover:bg-emerald-700 shadow-sm"
                    >
                      Grant / Reject Clearance
                    </button>
                  )}

                  <Link
                    href={`/applications/${app.id}`}
                    className="px-3 py-1.5 border border-slate-300 text-slate-700 rounded text-xs hover:bg-slate-50"
                  >
                    View Details
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Modal: Raise Query */}
        {activeModal === "QUERY" && selectedApp && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Issue Formal Deficiency Query on {selectedApp.application_number}
              </h3>
              <p className="text-xs text-slate-500">
                Specifying clear deficiencies halts the statutory clock and notifies the applicant to rectify.
              </p>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Query Subject / Title:</label>
                <input
                  type="text"
                  value={queryTitle}
                  onChange={(e) => setQueryTitle(e.target.value)}
                  placeholder="e.g. Inadequate Effluent Treatment Plant diagram"
                  className="w-full text-xs p-2 border border-slate-300 rounded"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Statutory Deficiency Remarks:</label>
                <textarea
                  rows={4}
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                  placeholder="Explain statutory violation, missing details, or required documents..."
                  className="w-full text-xs p-2 border border-slate-300 rounded"
                />
              </div>
              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  onClick={() => setActiveModal(null)}
                  className="px-3 py-1.5 border border-slate-300 text-slate-600 rounded text-xs"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRaiseQuery}
                  disabled={isProcessing}
                  className="px-4 py-1.5 bg-rose-600 text-white rounded text-xs font-semibold hover:bg-rose-700 disabled:opacity-50"
                >
                  {isProcessing ? "Issuing..." : "Issue Deficiency Note"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Schedule Inspection */}
        {activeModal === "INSPECTION" && selectedApp && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Schedule Physical Plant Inspection for {selectedApp.application_number}
              </h3>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Field Inspector User ID:</label>
                <input
                  type="text"
                  value={inspectorId}
                  onChange={(e) => setInspectorId(e.target.value)}
                  placeholder="Inspector UUID (or user ID holding INSPECTOR role)"
                  className="w-full text-xs p-2 border border-slate-300 rounded"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Scheduled Inspection Date & Time:</label>
                <input
                  type="datetime-local"
                  value={inspectDate}
                  onChange={(e) => setInspectDate(e.target.value)}
                  className="w-full text-xs p-2 border border-slate-300 rounded"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Inspector Instructions / Focus:</label>
                <textarea
                  rows={3}
                  value={inspectInstructions}
                  onChange={(e) => setInspectInstructions(e.target.value)}
                  placeholder="Focus on hazardous waste bunds, ETP aeration tank, fire exits..."
                  className="w-full text-xs p-2 border border-slate-300 rounded"
                />
              </div>
              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  onClick={() => setActiveModal(null)}
                  className="px-3 py-1.5 border border-slate-300 text-slate-600 rounded text-xs"
                >
                  Cancel
                </button>
                <button
                  onClick={handleScheduleInspection}
                  disabled={isProcessing}
                  className="px-4 py-1.5 bg-cyan-600 text-white rounded text-xs font-semibold hover:bg-cyan-700 disabled:opacity-50"
                >
                  {isProcessing ? "Scheduling..." : "Confirm Inspection"}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Modal: Final Determination */}
        {activeModal === "DETERMINE" && selectedApp && (
          <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-white rounded-lg border border-slate-200 shadow-xl max-w-lg w-full p-6 space-y-4">
              <h3 className="text-base font-bold text-slate-900">
                Statutory Determination on {selectedApp.application_number}
              </h3>
              <div className="flex items-center space-x-4">
                <label className="flex items-center space-x-2 text-xs font-medium cursor-pointer">
                  <input
                    type="radio"
                    checked={decision === "APPROVED"}
                    onChange={() => setDecision("APPROVED")}
                    className="text-emerald-600"
                  />
                  <span>✓ Grant Clearance (Approve)</span>
                </label>
                <label className="flex items-center space-x-2 text-xs font-medium cursor-pointer">
                  <input
                    type="radio"
                    checked={decision === "REJECTED"}
                    onChange={() => setDecision("REJECTED")}
                    className="text-red-600"
                  />
                  <span>✗ Refuse Clearance (Reject)</span>
                </label>
              </div>

              {decision === "APPROVED" && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Validity (Years):</label>
                  <input
                    type="number"
                    min={1}
                    max={25}
                    value={validityYears}
                    onChange={(e) => setValidityYears(parseInt(e.target.value) || 5)}
                    className="w-24 text-xs p-2 border border-slate-300 rounded"
                  />
                </div>
              )}

              {decision === "REJECTED" ? (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Statutory Grounds for Refusal:</label>
                  <textarea
                    rows={4}
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="Specific statutory act sections and non-compliance grounds..."
                    className="w-full text-xs p-2 border border-slate-300 rounded"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">Approval Order Remarks:</label>
                  <textarea
                    rows={3}
                    value={decisionRemarks}
                    onChange={(e) => setDecisionRemarks(e.target.value)}
                    placeholder="Special conditions of grant or operational mandates..."
                    className="w-full text-xs p-2 border border-slate-300 rounded"
                  />
                </div>
              )}

              <div className="flex items-center justify-end space-x-2 pt-2">
                <button
                  onClick={() => setActiveModal(null)}
                  className="px-3 py-1.5 border border-slate-300 text-slate-600 rounded text-xs"
                >
                  Cancel
                </button>
                <button
                  onClick={handleDetermination}
                  disabled={isProcessing}
                  className={`px-4 py-1.5 text-white rounded text-xs font-semibold disabled:opacity-50 ${
                    decision === "APPROVED" ? "bg-emerald-600 hover:bg-emerald-700" : "bg-red-600 hover:bg-red-700"
                  }`}
                >
                  {isProcessing ? "Processing..." : `Confirm ${decision}`}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

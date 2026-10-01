"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ApplicationDetail,
  getApplicationDetail,
  resubmitApplication,
  respondToQuery,
} from "@/lib/applications";

export default function ApplicationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params?.id as string;

  const [application, setApplication] = useState<ApplicationDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Response state for query
  const [activeQueryId, setActiveQueryId] = useState<string | null>(null);
  const [responseText, setResponseText] = useState("");
  const [responseDocId, setResponseDocId] = useState("");
  const [isSubmittingResponse, setIsSubmittingResponse] = useState(false);
  const [isResubmitting, setIsResubmitting] = useState(false);
  const [actionSuccessMsg, setActionSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!id) return;
      try {
        setIsLoading(true);
        setError(null);
        const data = await getApplicationDetail(id);
        setApplication(data);
      } catch (err: any) {
        console.error("Failed to load application detail:", err);
        setError(err.message || "Failed to load application detail.");
      } finally {
        setIsLoading(false);
      }
    }
    loadData();
  }, [id]);

  const handleRespondToQuery = async (queryId: string) => {
    if (!responseText.trim()) {
      alert("Please provide clarification remarks.");
      return;
    }
    try {
      setIsSubmittingResponse(true);
      setActionSuccessMsg(null);
      await respondToQuery(id, queryId, {
        response_text: responseText,
        response_document_id: responseDocId.trim() || undefined,
      });
      // Refresh detail
      const updated = await getApplicationDetail(id);
      setApplication(updated);
      setActiveQueryId(null);
      setResponseText("");
      setResponseDocId("");
      setActionSuccessMsg("Clarification submitted successfully!");
    } catch (err: any) {
      console.error("Failed to respond to query:", err);
      alert(err.message || "Failed to submit clarification.");
    } finally {
      setIsSubmittingResponse(false);
    }
  };

  const handleResubmit = async () => {
    try {
      setIsResubmitting(true);
      setActionSuccessMsg(null);
      const updated = await resubmitApplication(id, "All deficiency queries rectified.");
      setApplication(updated);
      setActionSuccessMsg("Application resubmitted successfully to Department Scrutiny Queue!");
    } catch (err: any) {
      console.error("Failed to resubmit application:", err);
      alert(err.message || "Failed to resubmit application.");
    } finally {
      setIsResubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-50 py-16 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gov-blue"></div>
        <p className="mt-3 text-sm text-slate-500">Loading statutory application workspace...</p>
      </div>
    );
  }

  if (error || !application) {
    return (
      <div className="min-h-screen bg-slate-50 py-12 px-4 max-w-3xl mx-auto">
        <div className="p-6 bg-red-50 border border-red-200 rounded-lg text-red-800 text-sm">
          {error || "Application not found"}
        </div>
        <div className="mt-4">
          <Link href="/applications" className="text-gov-blue hover:underline text-sm font-semibold">
            ← Back to Applications
          </Link>
        </div>
      </div>
    );
  }

  const openQueries = (application.queries || []).filter((q) => q.status === "OPEN");

  return (
    <div className="min-h-screen bg-slate-50 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-6">
        {/* Breadcrumb */}
        <nav className="text-xs text-slate-500 flex items-center space-x-1.5">
          <Link href="/dashboard" className="hover:text-gov-blue">Dashboard</Link>
          <span>/</span>
          <Link href="/applications" className="hover:text-gov-blue">Applications</Link>
          <span>/</span>
          <span className="font-mono text-slate-800 font-semibold">{application.application_number}</span>
        </nav>

        {/* Application Header Card */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <span className="text-xs font-mono font-bold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                  {application.application_number}
                </span>
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wide">
                  {application.department_code} • {application.department_name || "Regulatory Directorate"}
                </span>
              </div>
              <h1 className="mt-2 text-2xl font-bold text-slate-900 tracking-tight">
                {application.approval_title || application.approval_code}
              </h1>
              <p className="text-xs text-slate-500 mt-1">
                Filing Enterprise: <strong>{application.business_name}</strong> • Applied by:{" "}
                {application.applied_by_name || "Industrial Promoter"}
              </p>
            </div>

            <div className="text-right">
              <div className="text-xs font-medium text-slate-500 uppercase tracking-wider">Status</div>
              <div className="mt-1">
                <span
                  className={`inline-block px-3 py-1 text-xs font-bold rounded-full ${
                    application.status === "APPROVED"
                      ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                      : application.status === "QUERY_RAISED"
                      ? "bg-rose-100 text-rose-800 border border-rose-300"
                      : application.status === "REJECTED"
                      ? "bg-red-100 text-red-800 border border-red-300"
                      : "bg-blue-100 text-blue-800 border border-blue-200"
                  }`}
                >
                  {application.status}
                </span>
              </div>
              {application.sla_days_remaining !== null && (
                <div className="text-xs text-slate-500 mt-1">
                  SLA: <strong>{application.sla_days_remaining} days</strong> remaining
                </div>
              )}
            </div>
          </div>

          {/* Certificate Banner if Approved */}
          {application.status === "APPROVED" && (
            <div className="mt-6 p-4 rounded-lg bg-emerald-50 border border-emerald-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h4 className="text-sm font-semibold text-emerald-900">
                  🎉 Statutory Clearance Granted
                </h4>
                <p className="text-xs text-emerald-700">
                  Official License Number: <strong className="font-mono">{application.approval_certificate_number}</strong>
                  {application.certificate_valid_until && ` • Valid until: ${application.certificate_valid_until}`}
                </p>
              </div>
              <button
                onClick={() => alert(`Certificate ${application.approval_certificate_number} downloaded.`)}
                className="px-4 py-2 bg-emerald-600 text-white rounded text-xs font-semibold hover:bg-emerald-700 shadow-sm"
              >
                Download Official Certificate
              </button>
            </div>
          )}

          {/* Rejection Banner */}
          {application.status === "REJECTED" && (
            <div className="mt-6 p-4 rounded-lg bg-red-50 border border-red-200">
              <h4 className="text-sm font-semibold text-red-900">Clearance Refusal Grounds</h4>
              <p className="text-xs text-red-800 mt-1">{application.rejection_reason}</p>
            </div>
          )}
        </div>

        {/* Action Success Message */}
        {actionSuccessMsg && (
          <div className="p-4 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm font-medium">
            ✓ {actionSuccessMsg}
          </div>
        )}

        {/* Deficiency & Query Action Center (Fragment 83 & 84) */}
        {(application.queries || []).length > 0 && (
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Department Scrutiny Deficiency Notes ({application.queries.length})
                </h3>
                <p className="text-xs text-slate-500">
                  Clarification notes and document deficiency requisitions raised by the scrutiny officer.
                </p>
              </div>

              {/* Resubmit button if in QUERY_RAISED and all queries resolved */}
              {application.status === "QUERY_RAISED" && openQueries.length === 0 && (
                <button
                  onClick={handleResubmit}
                  disabled={isResubmitting}
                  className="px-4 py-2 bg-purple-600 text-white rounded-md text-xs font-semibold hover:bg-purple-700 shadow-sm disabled:opacity-50"
                >
                  {isResubmitting ? "Resubmitting..." : "Resubmit Application →"}
                </button>
              )}
            </div>

            <div className="space-y-3">
              {application.queries.map((q) => (
                <div
                  key={q.id}
                  className={`p-4 rounded-lg border ${
                    q.status === "OPEN"
                      ? "bg-rose-50/50 border-rose-200"
                      : "bg-slate-50 border-slate-200"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span className="text-base">{q.status === "OPEN" ? "⚠️" : "✓"}</span>
                      <h4 className="text-sm font-bold text-slate-900">{q.query_title}</h4>
                      <span
                        className={`px-2 py-0.5 text-2xs font-bold rounded-full ${
                          q.status === "OPEN"
                            ? "bg-rose-100 text-rose-800"
                            : "bg-emerald-100 text-emerald-800"
                        }`}
                      >
                        {q.status}
                      </span>
                    </div>
                    <span className="text-xs text-slate-500">
                      Raised by: {q.raised_by_name || "Scrutiny Officer"}
                    </span>
                  </div>

                  <p className="text-xs text-slate-700 mt-2 pl-6">{q.query_text}</p>

                  {/* If Resolved, show response */}
                  {q.status === "RESOLVED" && q.response_text && (
                    <div className="mt-3 pl-6 border-l-2 border-emerald-400 py-1 text-xs">
                      <span className="text-emerald-800 font-semibold">Promoter Response:</span>{" "}
                      <span className="text-slate-700">{q.response_text}</span>
                      {q.response_document_id && (
                        <div className="mt-1 text-2xs text-slate-500 font-mono">
                          Attached Document ID: {q.response_document_id}
                        </div>
                      )}
                    </div>
                  )}

                  {/* If Open and not active form, show respond button */}
                  {q.status === "OPEN" && activeQueryId !== q.id && (
                    <div className="mt-3 pl-6">
                      <button
                        onClick={() => {
                          setActiveQueryId(q.id);
                          setResponseText("");
                          setResponseDocId("");
                        }}
                        className="px-3 py-1.5 bg-rose-600 text-white rounded text-xs font-semibold hover:bg-rose-700"
                      >
                        Provide Response / Clarification
                      </button>
                    </div>
                  )}

                  {/* Active Form */}
                  {activeQueryId === q.id && (
                    <div className="mt-4 pl-6 space-y-3 bg-white p-4 rounded border border-rose-200">
                      <h5 className="text-xs font-bold text-slate-900">Your Response & Compliance Action</h5>
                      <div>
                        <label className="block text-2xs font-medium text-slate-600 mb-1">
                          Clarification Explanation:
                        </label>
                        <textarea
                          rows={3}
                          value={responseText}
                          onChange={(e) => setResponseText(e.target.value)}
                          placeholder="Provide detailed statutory clarification..."
                          className="w-full text-xs p-2.5 border border-slate-300 rounded focus:ring-1 focus:ring-gov-blue outline-none"
                        />
                      </div>
                      <div>
                        <label className="block text-2xs font-medium text-slate-600 mb-1">
                          Replacement / Supporting Document ID (Optional):
                        </label>
                        <input
                          type="text"
                          value={responseDocId}
                          onChange={(e) => setResponseDocId(e.target.value)}
                          placeholder="e.g. doc-uuid-from-document-vault"
                          className="w-full text-xs p-2 border border-slate-300 rounded"
                        />
                      </div>
                      <div className="flex items-center space-x-2">
                        <button
                          onClick={() => handleRespondToQuery(q.id)}
                          disabled={isSubmittingResponse}
                          className="px-3 py-1.5 bg-gov-blue text-white rounded text-xs font-semibold hover:bg-slate-800 disabled:opacity-50"
                        >
                          {isSubmittingResponse ? "Submitting..." : "Submit Clarification"}
                        </button>
                        <button
                          onClick={() => setActiveQueryId(null)}
                          className="px-3 py-1.5 border border-slate-300 text-slate-600 rounded text-xs hover:bg-slate-50"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Site Inspections Section (Fragments 87 & 88) */}
        {(application.inspections || []).length > 0 && (
          <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4">
            <h3 className="text-base font-semibold text-slate-900">Physical Site Verification</h3>
            <div className="space-y-3">
              {application.inspections.map((insp) => (
                <div key={insp.id} className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-slate-900">
                        Assigned Inspector: {insp.inspector_name || "Field Officer"}
                      </span>
                      <div className="text-xs text-slate-500">
                        Date: {new Date(insp.scheduled_date).toLocaleDateString()}
                      </div>
                    </div>
                    <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-cyan-100 text-cyan-800">
                      {insp.status}
                    </span>
                  </div>

                  {insp.instructions && (
                    <p className="text-xs text-slate-600 mt-2">
                      <strong>Instructions:</strong> {insp.instructions}
                    </p>
                  )}

                  {insp.findings && (
                    <div className="mt-3 p-3 bg-white rounded border border-slate-200 text-xs">
                      <div className="font-semibold text-slate-800">Findings:</div>
                      <p className="text-slate-700 mt-1">{insp.findings}</p>
                      {insp.recommendation && (
                        <div className="mt-2 text-2xs font-bold text-emerald-800">
                          Recommendation: {insp.recommendation}
                        </div>
                      )}
                      {insp.geo_latitude && insp.geo_longitude && (
                        <div className="mt-1 text-2xs text-slate-500 font-mono">
                          GPS Coordinates: {insp.geo_latitude}, {insp.geo_longitude}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scrutiny Status Audit History (Fragment 79) */}
        <div className="bg-white rounded-lg border border-slate-200 shadow-sm p-6 space-y-4">
          <h3 className="text-base font-semibold text-slate-900">Regulatory Scrutiny Audit Trail</h3>
          <div className="space-y-4 relative pl-4 border-l-2 border-slate-200 ml-2">
            {(application.status_history || []).map((h) => (
              <div key={h.id} className="relative">
                <div className="absolute -left-[23px] top-1.5 h-3.5 w-3.5 rounded-full bg-gov-blue border-2 border-white"></div>
                <div className="text-xs">
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-slate-900">{h.action}</span>
                    <span className="text-slate-500">
                      {h.from_status ? `${h.from_status} → ` : ""}
                      <strong className="text-slate-700">{h.to_status}</strong>
                    </span>
                    <span className="text-2xs text-slate-400">
                      {new Date(h.created_at).toLocaleString()}
                    </span>
                  </div>
                  {h.remarks && <p className="text-slate-600 mt-1">{h.remarks}</p>}
                  {h.changed_by_name && (
                    <div className="text-2xs text-slate-500 mt-0.5">By: {h.changed_by_name}</div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

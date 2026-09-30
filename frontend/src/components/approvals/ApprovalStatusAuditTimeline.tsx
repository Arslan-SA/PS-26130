"use client";

import React, { useState } from "react";
import {
  ApprovalRequirement,
  ApprovalStatusHistory,
  RequirementStatus,
  updateRequirementStatus,
} from "@/lib/approvals";

interface ApprovalStatusAuditTimelineProps {
  requirement: ApprovalRequirement;
  history: ApprovalStatusHistory[];
  onHistoryUpdated: (newHistory: ApprovalStatusHistory[], updatedReq: ApprovalRequirement) => void;
}

export function ApprovalStatusAuditTimeline({
  requirement,
  history,
  onHistoryUpdated,
}: ApprovalStatusAuditTimelineProps) {
  const [isUpdating, setIsUpdating] = useState(false);
  const [targetStatus, setTargetStatus] = useState<RequirementStatus>(requirement.status);
  const [remarks, setRemarks] = useState("");
  const [referenceNumber, setReferenceNumber] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const getStatusColor = (status: RequirementStatus) => {
    switch (status) {
      case "APPROVED":
        return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
      case "UNDER_REVIEW":
        return "bg-sky-500/10 text-sky-400 border-sky-500/30";
      case "SUBMITTED":
        return "bg-blue-500/10 text-blue-400 border-blue-500/30";
      case "IN_PROGRESS":
        return "bg-amber-500/10 text-amber-400 border-amber-500/30";
      case "REJECTED":
        return "bg-rose-500/10 text-rose-400 border-rose-500/30";
      case "EXEMPTED":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      default:
        return "bg-slate-800 text-slate-400 border-slate-700";
    }
  };

  const handleStatusSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (targetStatus === requirement.status && !remarks.trim()) {
      setErrorMsg("Please select a different status or enter update remarks.");
      return;
    }

    try {
      setSubmitting(true);
      setErrorMsg(null);
      const updatedReq = await updateRequirementStatus(requirement.id, {
        status: targetStatus,
        remarks: remarks.trim() || undefined,
        reference_number: referenceNumber.trim() || undefined,
      });

      // Construct optimistic history entry
      const newEntry: ApprovalStatusHistory = {
        id: `temp-${Date.now()}`,
        requirement_id: requirement.id,
        business_id: requirement.business_id,
        from_status: requirement.status,
        to_status: targetStatus,
        remarks: remarks.trim() || null,
        reference_number: referenceNumber.trim() || null,
        created_at: new Date().toISOString(),
      };

      onHistoryUpdated([newEntry, ...history], updatedReq);
      setIsUpdating(false);
      setRemarks("");
      setReferenceNumber("");
    } catch (err: any) {
      console.error("Failed to update status:", err);
      setErrorMsg(err.message || "Failed to record status transition.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-6 space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            <span>📜</span> Regulatory Lifecycle Audit Trail
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Immutable transition log with timestamps, officer notes, and statutory receipt numbers
          </p>
        </div>
        <button
          onClick={() => setIsUpdating(!isUpdating)}
          className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-sm"
        >
          {isUpdating ? "Cancel" : "Update Status →"}
        </button>
      </div>

      {/* Transition Update Form */}
      {isUpdating && (
        <form
          onSubmit={handleStatusSubmit}
          className="p-5 rounded-xl bg-slate-950/70 border border-indigo-500/30 space-y-4 animate-in fade-in"
        >
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-semibold text-indigo-300">
              Record New Statutory Transition
            </h4>
            <span className="text-xs text-slate-400">
              Current: <strong className="text-slate-200">{requirement.status}</strong>
            </span>
          </div>

          {errorMsg && (
            <div className="p-3 rounded-lg bg-rose-950/40 border border-rose-800/60 text-xs text-rose-300">
              {errorMsg}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Target Status
              </label>
              <select
                value={targetStatus}
                onChange={(e) => setTargetStatus(e.target.value as RequirementStatus)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                <option value="NOT_STARTED">NOT_STARTED</option>
                <option value="IN_PROGRESS">IN_PROGRESS (Preparing dossier)</option>
                <option value="SUBMITTED">SUBMITTED (Filing complete)</option>
                <option value="UNDER_REVIEW">UNDER_REVIEW (Department scrutiny)</option>
                <option value="APPROVED">APPROVED (Clearance granted)</option>
                <option value="REJECTED">REJECTED (Refusal / Deficiencies)</option>
                <option value="EXEMPTED">EXEMPTED (Statutory waiver)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Reference / Challan / ARN Number
              </label>
              <input
                type="text"
                placeholder="e.g. ARN-PCB-2026-9921"
                value={referenceNumber}
                onChange={(e) => setReferenceNumber(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Remarks / Regulatory Notes
            </label>
            <textarea
              rows={2}
              placeholder="e.g. Scrutiny cleared by Assistant Environmental Engineer; inspection scheduled."
              value={remarks}
              onChange={(e) => setRemarks(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setIsUpdating(false)}
              className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 text-white shadow-md shadow-indigo-600/20"
            >
              {submitting ? "Recording..." : "Save Transition Audit"}
            </button>
          </div>
        </form>
      )}

      {/* Timeline List */}
      <div className="space-y-4">
        {history.length === 0 ? (
          <div className="p-8 text-center rounded-xl bg-slate-950/30 border border-slate-800/80">
            <p className="text-xs text-slate-400">
              No status transitions recorded yet for this requirement. Current baseline status:{" "}
              <span className="font-semibold text-slate-300">{requirement.status}</span>.
            </p>
          </div>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-slate-800">
            {history.map((item, index) => (
              <div key={item.id || index} className="relative group">
                {/* Node dot */}
                <span
                  className={`absolute -left-[27px] top-1.5 w-3 h-3 rounded-full border-2 border-slate-950 ${
                    item.to_status === "APPROVED"
                      ? "bg-emerald-400 shadow-sm shadow-emerald-400/50"
                      : item.to_status === "UNDER_REVIEW" || item.to_status === "SUBMITTED"
                      ? "bg-sky-400"
                      : item.to_status === "REJECTED"
                      ? "bg-rose-400"
                      : "bg-indigo-400"
                  }`}
                />

                <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/80 space-y-2 group-hover:border-slate-700 transition-colors">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      {item.from_status && (
                        <>
                          <span
                            className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${getStatusColor(
                              item.from_status
                            )}`}
                          >
                            {item.from_status}
                          </span>
                          <span className="text-xs text-slate-500">→</span>
                        </>
                      )}
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-semibold border ${getStatusColor(
                          item.to_status
                        )}`}
                      >
                        {item.to_status}
                      </span>
                    </div>

                    <time className="text-[11px] text-slate-500 font-mono">
                      {new Date(item.created_at).toLocaleString("en-IN", {
                        dateStyle: "medium",
                        timeStyle: "short",
                      })}
                    </time>
                  </div>

                  {item.reference_number && (
                    <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-emerald-400 border border-slate-700">
                      <span>🏷️ Reference:</span>
                      <strong className="text-white">{item.reference_number}</strong>
                    </div>
                  )}

                  {item.remarks && (
                    <p className="text-xs text-slate-300 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60">
                      {item.remarks}
                    </p>
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

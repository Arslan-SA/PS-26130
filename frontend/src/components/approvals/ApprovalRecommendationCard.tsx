"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ApprovalRequirement,
  RequirementStage,
  RequirementStatus,
  updateRequirementStatus,
} from "@/lib/approvals";

interface Props {
  requirement: ApprovalRequirement;
  onStatusUpdated?: (updated: ApprovalRequirement) => void;
}

export default function ApprovalRecommendationCard({
  requirement,
  onStatusUpdated,
}: Props) {
  const [isUpdating, setIsUpdating] = useState(false);
  const [currentStatus, setCurrentStatus] = useState<RequirementStatus>(requirement.status);

  const handleStatusChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value as RequirementStatus;
    try {
      setIsUpdating(true);
      const updated = await updateRequirementStatus(requirement.id, newStatus);
      setCurrentStatus(newStatus);
      if (onStatusUpdated) onStatusUpdated(updated);
    } catch (err) {
      console.error("Failed to update requirement status:", err);
    } finally {
      setIsUpdating(false);
    }
  };

  const getStageBadge = (stage: RequirementStage) => {
    switch (stage) {
      case "PRE_ESTABLISHMENT":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950/80 text-emerald-300 border border-emerald-700/50">
            Phase 1 • Pre-Establishment
          </span>
        );
      case "PRE_COMMISSIONING":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-950/80 text-blue-300 border border-blue-700/50">
            Phase 2 • Pre-Commissioning
          </span>
        );
      case "POST_COMMISSIONING":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-950/80 text-amber-300 border border-amber-700/50">
            Phase 3 • Post-Commissioning
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-800 text-slate-300">
            Regular Operations
          </span>
        );
    }
  };

  const getStatusBadge = (st: RequirementStatus) => {
    switch (st) {
      case "APPROVED":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      case "SUBMITTED":
      case "UNDER_REVIEW":
        return "bg-purple-500/20 text-purple-300 border-purple-500/40";
      case "IN_PROGRESS":
        return "bg-blue-500/20 text-blue-300 border-blue-500/40";
      case "EXEMPTED":
        return "bg-slate-700/40 text-slate-400 border-slate-600/40";
      default:
        return "bg-amber-500/20 text-amber-300 border-amber-500/40";
    }
  };

  return (
    <div className="group relative bg-slate-900/70 border border-slate-800 hover:border-slate-700 rounded-xl p-6 transition-all duration-200 shadow-lg hover:shadow-indigo-500/5 backdrop-blur-sm">
      {/* Top Meta Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex items-center space-x-2">
          <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 font-semibold tracking-wider">
            {requirement.approval?.code || "REQ"}
          </span>
          {getStageBadge(requirement.stage)}
        </div>
        <div className="flex items-center space-x-2">
          {requirement.is_mandatory ? (
            <span className="text-xs font-semibold px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/40">
              Mandatory
            </span>
          ) : (
            <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              Conditional
            </span>
          )}
        </div>
      </div>

      {/* Main Clearance Title */}
      <h3 className="text-lg font-bold text-white mb-1 group-hover:text-indigo-300 transition-colors">
        {requirement.approval?.title || requirement.approval_id}
      </h3>
      <p className="text-xs text-slate-400 mb-4 flex items-center gap-1.5">
        <span className="font-medium text-slate-300">
          {requirement.approval?.issuing_authority || requirement.approval?.department_code}
        </span>
        {requirement.approval?.statutory_act && (
          <>
            <span>•</span>
            <span className="text-slate-400 italic">
              {requirement.approval.statutory_act}
            </span>
          </>
        )}
      </p>

      {/* Trigger Rationale Banner */}
      <div className="mb-4 p-3 rounded-lg bg-indigo-950/30 border border-indigo-900/40 text-xs text-indigo-200 leading-relaxed">
        <span className="font-semibold text-indigo-300 uppercase tracking-wider block text-[10px] mb-1">
          Statutory Justification
        </span>
        {requirement.trigger_reason}
      </div>

      {/* Metrics Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mb-5 p-3 rounded-lg bg-slate-950/50 border border-slate-800/60 text-xs">
        <div>
          <span className="text-slate-400 block text-[11px]">SLA Target</span>
          <span className="text-white font-semibold">
            {requirement.sla_deadline_days} Calendar Days
          </span>
        </div>
        <div>
          <span className="text-slate-400 block text-[11px]">Estimated Fee</span>
          <span className="text-emerald-400 font-semibold">
            ₹{requirement.estimated_fee.toLocaleString("en-IN")}
          </span>
        </div>
        <div className="col-span-2 sm:col-span-1">
          <span className="text-slate-400 block text-[11px]">Priority</span>
          <span className="text-amber-400 font-semibold">
            Tier {requirement.priority} (Critical Path)
          </span>
        </div>
      </div>

      {/* Bottom Action Footer */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-slate-800/80">
        <div className="flex items-center space-x-2">
          <label htmlFor={`status-${requirement.id}`} className="text-xs text-slate-400 font-medium">
            Status:
          </label>
          <select
            id={`status-${requirement.id}`}
            value={currentStatus}
            disabled={isUpdating}
            onChange={handleStatusChange}
            aria-label="Requirement Status"
            className={`text-xs px-2.5 py-1 rounded-md border font-medium bg-slate-900 focus:ring-1 focus:ring-indigo-500 outline-none ${getStatusBadge(
              currentStatus
            )}`}
          >
            <option value="NOT_STARTED">Not Started</option>
            <option value="IN_PROGRESS">In Progress</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="APPROVED">Approved</option>
            <option value="EXEMPTED">Exempted</option>
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <Link
            href={`/approvals/${requirement.id}`}
            className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-sm shadow-indigo-600/20"
          >
            Checklist & Guide →
          </Link>
        </div>
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ActionPriority,
  ActionType,
  NextActionItem,
  NextActionSummary,
} from "@/lib/approvals";

interface NextActionQueueViewProps {
  summary: NextActionSummary;
}

export function NextActionQueueView({ summary }: NextActionQueueViewProps) {
  const [selectedFilter, setSelectedFilter] = useState<string>("ALL");

  const filteredActions = summary.actions.filter((action) => {
    if (selectedFilter === "ALL") return true;
    if (selectedFilter === "READY") {
      return ["APPLY_NOW", "PREPARE_DOCS", "PAY_FEES"].includes(action.action_type);
    }
    if (selectedFilter === "CRITICAL") {
      return action.is_critical_path && ["APPLY_NOW", "PREPARE_DOCS"].includes(action.action_type);
    }
    if (selectedFilter === "BLOCKED") {
      return action.action_type === "RESOLVE_PREREQUISITES";
    }
    if (selectedFilter === "UNDER_REVIEW") {
      return action.action_type === "TRACK_SLA";
    }
    if (selectedFilter === "COMPLETED") {
      return action.action_type === "DOWNLOAD_CERTIFICATE";
    }
    return true;
  });

  const getPriorityBadge = (priority: ActionPriority) => {
    switch (priority) {
      case "CRITICAL":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20 animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
            Critical Path
          </span>
        );
      case "HIGH":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            High Priority
          </span>
        );
      case "MEDIUM":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400"></span>
            Normal Track
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            Low / Deferred
          </span>
        );
    }
  };

  const getActionTypeBadge = (type: ActionType) => {
    switch (type) {
      case "APPLY_NOW":
        return (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            Ready to Apply
          </span>
        );
      case "PREPARE_DOCS":
        return (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
            Complete Dossier
          </span>
        );
      case "TRACK_SLA":
        return (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-sky-500/10 text-sky-400 border border-sky-500/20">
            Under Review (SLA)
          </span>
        );
      case "RESOLVE_PREREQUISITES":
        return (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
            Prerequisites Pending
          </span>
        );
      case "DOWNLOAD_CERTIFICATE":
        return (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-teal-500/10 text-teal-400 border border-teal-500/20">
            Approved & Active
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-300">
            {type}
          </span>
        );
    }
  };

  const topAction = summary.top_immediate_action;

  return (
    <div className="space-y-8">
      {/* Metric Cards Header */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Ready to Act</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-emerald-400">{summary.ready_to_act_count}</span>
            <span className="text-xs text-slate-500">clearances</span>
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Critical Path</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-rose-400">{summary.critical_path_actions_count}</span>
            <span className="text-xs text-slate-500">bottlenecks</span>
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Blocked (Prereqs)</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-amber-400">{summary.blocked_count}</span>
            <span className="text-xs text-slate-500">waiting</span>
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">In Review</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-sky-400">{summary.under_review_count}</span>
            <span className="text-xs text-slate-500">processing</span>
          </div>
        </div>
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 backdrop-blur-sm">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wider">Completed</p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-teal-400">{summary.completed_count}</span>
            <span className="text-xs text-slate-500">approved</span>
          </div>
        </div>
      </div>

      {/* Hero Spotlight: Top Immediate Recommended Action */}
      {topAction && (
        <div className="relative overflow-hidden rounded-2xl border border-emerald-500/30 bg-gradient-to-br from-emerald-950/40 via-slate-900/80 to-slate-950/80 p-6 shadow-2xl backdrop-blur-md">
          <div className="absolute top-0 right-0 -mr-16 -mt-16 w-64 h-64 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center px-2.5 py-0.5 rounded text-xs font-bold bg-emerald-500 text-slate-950">
                  🎯 RECOMMENDED IMMEDIATE NEXT STEP
                </span>
                {getPriorityBadge(topAction.priority)}
                {getActionTypeBadge(topAction.action_type)}
              </div>
              <h3 className="text-xl md:text-2xl font-bold text-white tracking-tight">
                {topAction.headline}
              </h3>
              <p className="text-sm text-slate-300 max-w-3xl leading-relaxed">
                {topAction.rationale}
              </p>
              <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
                <span>
                  <strong className="text-slate-300">Department:</strong> {topAction.department_code}
                </span>
                <span>•</span>
                <span>
                  <strong className="text-slate-300">Statutory SLA:</strong> {topAction.sla_days} working days
                </span>
                <span>•</span>
                <span>
                  <strong className="text-slate-300">Estimated Fee:</strong> ₹{topAction.estimated_fee.toLocaleString("en-IN")}
                </span>
              </div>
            </div>
            <div className="flex-shrink-0">
              <Link
                href={topAction.target_url}
                className="inline-flex items-center justify-center px-5 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold text-sm shadow-lg shadow-emerald-500/20 transition-all hover:scale-[1.02]"
              >
                Execute Clearance Now →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Filter Tabs & Quick Nav */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800">
        <div className="flex flex-wrap gap-2">
          {[
            { id: "ALL", label: `All Actions (${summary.actions.length})` },
            { id: "READY", label: `Ready to Act (${summary.ready_to_act_count})` },
            { id: "CRITICAL", label: `Critical Path (${summary.critical_path_actions_count})` },
            { id: "BLOCKED", label: `Prereqs Pending (${summary.blocked_count})` },
            { id: "UNDER_REVIEW", label: `In Review (${summary.under_review_count})` },
            { id: "COMPLETED", label: `Approved (${summary.completed_count})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedFilter(tab.id)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                selectedFilter === tab.id
                  ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40"
                  : "bg-slate-800/40 text-slate-400 hover:bg-slate-800 hover:text-slate-200"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* View Switchers */}
        <div className="flex items-center gap-2 text-xs">
          <Link
            href="/approvals"
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
          >
            📋 Catalog
          </Link>
          <Link
            href="/approvals/graph"
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
          >
            🕸️ DAG Graph
          </Link>
          <Link
            href="/approvals/roadmap"
            className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-medium"
          >
            📅 Gantt Roadmap
          </Link>
        </div>
      </div>

      {/* Action Queue List */}
      <div className="space-y-4">
        {filteredActions.length === 0 ? (
          <div className="text-center py-12 rounded-xl bg-slate-900/40 border border-slate-800">
            <p className="text-slate-400 text-sm">No statutory clearance actions in this filter.</p>
          </div>
        ) : (
          filteredActions.map((action) => (
            <div
              key={action.approval_code}
              className={`p-5 rounded-xl border transition-all ${
                action.is_critical_path && action.action_type === "APPLY_NOW"
                  ? "bg-slate-900/90 border-rose-500/40 shadow-lg shadow-rose-500/5 hover:border-rose-500/70"
                  : "bg-slate-900/50 border-slate-800/80 hover:border-slate-700"
              }`}
            >
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div className="space-y-2 flex-grow">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-emerald-400 border border-slate-700">
                      {action.approval_code}
                    </span>
                    {getPriorityBadge(action.priority)}
                    {getActionTypeBadge(action.action_type)}
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-800/80 text-slate-400">
                      {action.stage.replace("_", " ")}
                    </span>
                  </div>

                  <h4 className="text-base font-semibold text-white">
                    {action.headline}
                  </h4>

                  <p className="text-xs text-slate-400 max-w-3xl">
                    {action.rationale}
                  </p>

                  {/* Prerequisites blocked badge */}
                  {action.blocked_by && action.blocked_by.length > 0 && (
                    <div className="flex items-center gap-2 pt-1 text-xs text-rose-400">
                      <span>⚠️ Awaiting Prerequisites:</span>
                      <div className="flex flex-wrap gap-1">
                        {action.blocked_by.map((code) => (
                          <span
                            key={code}
                            className="px-1.5 py-0.5 rounded bg-rose-500/10 border border-rose-500/30 font-mono font-medium text-[11px]"
                          >
                            {code}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Right side stats & CTA */}
                <div className="flex sm:flex-row lg:flex-col items-start lg:items-end justify-between lg:justify-center gap-3 shrink-0 pt-2 lg:pt-0 border-t lg:border-t-0 border-slate-800">
                  <div className="text-right text-xs space-y-0.5">
                    <div className="text-slate-400">
                      SLA: <span className="font-medium text-slate-200">{action.sla_days} days</span>
                    </div>
                    <div className="text-slate-400">
                      Fee: <span className="font-medium text-slate-200">₹{action.estimated_fee.toLocaleString("en-IN")}</span>
                    </div>
                  </div>

                  <Link
                    href={action.target_url}
                    className="inline-flex items-center justify-center px-4 py-2 rounded-lg bg-slate-800 hover:bg-emerald-600 hover:text-white text-emerald-400 font-medium text-xs transition-colors border border-slate-700 hover:border-emerald-500"
                  >
                    View Checklist & Apply →
                  </Link>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

"use client";

import React, { useState } from "react";
import Link from "next/link";
import { RoadmapActivity, RoadmapPlan } from "@/lib/approvals";

interface Props {
  plan: RoadmapPlan;
}

export default function PersonalizedRoadmapView({ plan }: Props) {
  const [activePhase, setActivePhase] = useState<string>("ALL");

  const filteredActivities = plan.activities.filter((act) => {
    if (activePhase === "ALL") return true;
    return act.stage === activePhase;
  });

  const totalDays = Math.max(plan.total_calendar_days, 1);

  return (
    <div className="space-y-8">
      {/* Top Lifecycle KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl">
          <span className="text-xs text-slate-400 font-medium">Timeline Commencement</span>
          <div className="mt-2 text-xl font-bold text-white">
            {new Date(plan.base_start_date).toLocaleDateString("en-IN", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Dossier initiation baseline</p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl">
          <span className="text-xs text-slate-400 font-medium">Projected Commissioning</span>
          <div className="mt-2 text-xl font-bold text-emerald-400">
            {new Date(plan.projected_commissioning_date).toLocaleDateString("en-IN", {
              day: "numeric",
              month: "short",
              year: "numeric",
            })}
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Statutory readiness target</p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl">
          <span className="text-xs text-slate-400 font-medium">Total Execution Span</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-black text-amber-400">
              {plan.total_calendar_days}
            </span>
            <span className="text-xs text-slate-400 font-semibold">Days</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Parallel compressed turnaround</p>
        </div>

        <div className="p-5 bg-slate-900/80 border border-slate-800 rounded-xl">
          <span className="text-xs text-slate-400 font-medium">Critical Path Lead Time</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-black text-indigo-400">
              {plan.critical_path_days}
            </span>
            <span className="text-xs text-slate-400 font-semibold">Days</span>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Unavoidable sequential bottleneck</p>
        </div>
      </div>

      {/* Milestone Phase Progression */}
      <div className="space-y-4">
        <h3 className="text-base font-bold text-white tracking-wide">
          Statutory Commissioning Milestones
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {plan.milestones.map((m, idx) => (
            <div
              key={m.phase_id}
              onClick={() => setActivePhase(activePhase === m.phase_id ? "ALL" : m.phase_id)}
              className={`p-5 rounded-2xl border transition-all cursor-pointer ${
                activePhase === m.phase_id
                  ? "bg-indigo-950/40 border-indigo-500 ring-1 ring-indigo-500"
                  : "bg-slate-900/60 border-slate-800 hover:border-slate-700"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-bold text-indigo-400 uppercase tracking-wider">
                  Phase {idx + 1}
                </span>
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                  Days {m.start_day} - {m.finish_day}
                </span>
              </div>
              <h4 className="text-sm font-bold text-white">{m.title}</h4>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2 leading-relaxed">
                {m.description}
              </p>

              <div className="mt-4 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-slate-400">{m.activity_count} Clearances</span>
                <span className="font-bold text-emerald-400">
                  ₹{m.total_estimated_fee.toLocaleString("en-IN")}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Visual Gantt Schedule Timeline */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-base font-bold text-white">Execution Timeline & Gantt Schedule</h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Horizontal bars represent statutory review windows based on Public Service Guarantee SLAs.
            </p>
          </div>

          {/* Phase Filter Tabs */}
          <div className="flex flex-wrap gap-2 text-xs">
            <button
              onClick={() => setActivePhase("ALL")}
              className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                activePhase === "ALL"
                  ? "bg-indigo-600 text-white"
                  : "bg-slate-800 text-slate-400 hover:text-white"
              }`}
            >
              All Phases
            </button>
            {plan.milestones.map((m) => (
              <button
                key={m.phase_id}
                onClick={() => setActivePhase(m.phase_id)}
                className={`px-3 py-1.5 rounded-lg font-semibold transition-all ${
                  activePhase === m.phase_id
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-800 text-slate-400 hover:text-white"
                }`}
              >
                {m.phase_id.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {/* Timeline Row Items */}
        <div className="space-y-4">
          {filteredActivities.map((act) => {
            const leftPercent = (act.start_day_offset / totalDays) * 100;
            const widthPercent = Math.max((act.sla_days / totalDays) * 100, 8);

            return (
              <div
                key={act.approval_code}
                className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl space-y-3"
              >
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold border border-slate-700">
                      {act.approval_code}
                    </span>
                    <span className="text-xs font-bold text-white">{act.title}</span>
                    {act.is_critical && (
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500 text-slate-950">
                        Critical
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-slate-400">
                      {new Date(act.scheduled_start).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                      })}{" "}
                      -{" "}
                      {new Date(act.scheduled_finish).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                      })}
                    </span>
                    <Link
                      href={`/approvals/${act.requirement_id}`}
                      className="text-indigo-400 hover:text-indigo-300 font-semibold"
                    >
                      Dossier →
                    </Link>
                  </div>
                </div>

                {/* Progress Bar Container */}
                <div className="relative w-full bg-slate-900 rounded-lg h-6 p-1 border border-slate-800">
                  <div
                    className={`h-full rounded transition-all duration-300 flex items-center justify-between px-2 text-[10px] font-bold ${
                      act.is_critical
                        ? "bg-gradient-to-r from-amber-600 to-amber-500 text-slate-950 shadow-sm shadow-amber-500/30"
                        : "bg-indigo-600 text-white"
                    }`}
                    style={{
                      marginLeft: `${leftPercent}%`,
                      width: `${widthPercent}%`,
                    }}
                  >
                    <span className="truncate">{act.sla_days}d</span>
                    <span className="truncate font-normal hidden sm:inline">
                      ₹{act.estimated_fee.toLocaleString("en-IN")}
                    </span>
                  </div>
                </div>

                {/* Prerequisites info */}
                {act.prerequisites.length > 0 && (
                  <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
                    <span>Prerequisites:</span>
                    <span className="font-mono text-amber-300 font-medium">
                      {act.prerequisites.join(", ")}
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

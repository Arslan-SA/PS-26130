"use client";

import React, { useState } from "react";
import Link from "next/link";
import { DependencyGraphResponse, GraphNode } from "@/lib/approvals";

interface Props {
  graph: DependencyGraphResponse;
}

export default function DependencyGraphView({ graph }: Props) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Group nodes by statutory commissioning stage
  const preEstablishmentNodes = graph.nodes.filter(
    (n) => n.stage === "PRE_ESTABLISHMENT"
  );
  const preCommissioningNodes = graph.nodes.filter(
    (n) => n.stage === "PRE_COMMISSIONING"
  );
  const postCommissioningNodes = graph.nodes.filter(
    (n) => n.stage === "POST_COMMISSIONING" || n.stage === "REGULAR_OPERATIONS"
  );

  const criticalPathSet = new Set(graph.critical_path);

  // Compute incoming and outgoing dependencies for each node
  const incomingMap: Record<string, string[]> = {};
  const outgoingMap: Record<string, string[]> = {};
  graph.edges.forEach((edge) => {
    if (!incomingMap[edge.target]) incomingMap[edge.target] = [];
    incomingMap[edge.target].push(edge.source);

    if (!outgoingMap[edge.source]) outgoingMap[edge.source] = [];
    outgoingMap[edge.source].push(edge.target);
  });

  const selectedNode = selectedNodeId
    ? graph.nodes.find((n) => n.id === selectedNodeId)
    : null;

  return (
    <div className="space-y-6">
      {/* Top Critical Path Banner */}
      <div className="p-6 bg-gradient-to-r from-amber-950/40 via-slate-900/90 to-indigo-950/40 border border-amber-800/40 rounded-2xl shadow-xl backdrop-blur-md">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </span>
              <h2 className="text-lg font-bold text-white">
                Statutory Critical Turnaround Path
              </h2>
            </div>
            <p className="text-xs text-slate-300 mt-1">
              Minimum unavoidable sequential duration before commercial factory operations can begin:
            </p>
          </div>

          <div className="flex items-center gap-4 bg-slate-950/80 px-5 py-3 rounded-xl border border-slate-800">
            <div>
              <span className="text-[11px] text-slate-400 uppercase tracking-wider block font-semibold">
                Sequential SLA Lead Time
              </span>
              <span className="text-2xl font-black text-amber-400">
                {graph.critical_path_days} Calendar Days
              </span>
            </div>
          </div>
        </div>

        {/* Critical Path Flow Strip */}
        <div className="mt-4 pt-4 border-t border-slate-800/80 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400 font-medium mr-1">Critical Chain:</span>
          {graph.critical_path.map((code, idx) => (
            <React.Fragment key={code}>
              <button
                onClick={() => setSelectedNodeId(code)}
                className={`font-mono font-bold px-3 py-1 rounded-lg border transition-all ${
                  selectedNodeId === code
                    ? "bg-amber-500 text-slate-950 border-amber-400 shadow-md shadow-amber-500/30"
                    : "bg-amber-950/60 text-amber-300 border-amber-700/60 hover:bg-amber-900/60"
                }`}
              >
                {code}
              </button>
              {idx < graph.critical_path.length - 1 && (
                <span className="text-amber-500 font-bold">→</span>
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {/* Selected Node Inspector Flyout */}
      {selectedNode && (
        <div className="p-5 bg-indigo-950/40 border border-indigo-700/60 rounded-xl space-y-3 animate-in fade-in duration-200">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs px-2 py-0.5 rounded bg-indigo-900 text-indigo-300 font-bold">
                {selectedNode.id}
              </span>
              <h3 className="text-base font-bold text-white">{selectedNode.title}</h3>
            </div>
            <button
              onClick={() => setSelectedNodeId(null)}
              className="text-xs text-slate-400 hover:text-white"
            >
              ✕ Close
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
              <span className="text-slate-400 block mb-1">Prerequisites (Must complete first):</span>
              {incomingMap[selectedNode.id]?.length ? (
                <div className="flex flex-wrap gap-1">
                  {incomingMap[selectedNode.id].map((prereq) => (
                    <span
                      key={prereq}
                      className="font-mono px-2 py-0.5 rounded bg-slate-800 text-amber-300 font-semibold"
                    >
                      {prereq}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-emerald-400 font-medium">None (Root clearance)</span>
              )}
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800">
              <span className="text-slate-400 block mb-1">Unlocks (Next downstream):</span>
              {outgoingMap[selectedNode.id]?.length ? (
                <div className="flex flex-wrap gap-1">
                  {outgoingMap[selectedNode.id].map((downstream) => (
                    <span
                      key={downstream}
                      className="font-mono px-2 py-0.5 rounded bg-slate-800 text-indigo-300 font-semibold"
                    >
                      {downstream}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-slate-400 italic">Terminal clearance</span>
              )}
            </div>

            <div className="p-3 bg-slate-950/60 rounded-lg border border-slate-800 flex items-center justify-between">
              <div>
                <span className="text-slate-400 block text-[11px]">Readiness Status</span>
                <span
                  className={`font-semibold ${
                    selectedNode.is_unlocked ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  {selectedNode.is_unlocked ? "✓ Ready to Apply" : "🔒 Prerequisites Incomplete"}
                </span>
              </div>
              <Link
                href={`/approvals/${selectedNode.requirement_id}`}
                className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                View Dossier →
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* 3-Lane Stage Architecture Graph */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Lane 1: Pre-Establishment */}
        <div className="space-y-4">
          <div className="p-3.5 bg-emerald-950/30 border border-emerald-800/40 rounded-xl">
            <span className="text-[10px] font-mono font-bold text-emerald-400 uppercase tracking-wider block">
              Stage 1
            </span>
            <h3 className="text-sm font-bold text-white">Pre-Establishment Clearances</h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Mandatory before breaking ground or initiating civil construction.
            </p>
          </div>

          <div className="space-y-3">
            {preEstablishmentNodes.map((node) => (
              <NodeCard
                key={node.id}
                node={node}
                isCritical={criticalPathSet.has(node.id)}
                isSelected={selectedNodeId === node.id}
                onSelect={() => setSelectedNodeId(node.id)}
              />
            ))}
          </div>
        </div>

        {/* Lane 2: Pre-Commissioning */}
        <div className="space-y-4">
          <div className="p-3.5 bg-blue-950/30 border border-blue-800/40 rounded-xl">
            <span className="text-[10px] font-mono font-bold text-blue-400 uppercase tracking-wider block">
              Stage 2
            </span>
            <h3 className="text-sm font-bold text-white">Pre-Commissioning Clearances</h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Required before trial production runs, power energization, or storage.
            </p>
          </div>

          <div className="space-y-3">
            {preCommissioningNodes.map((node) => (
              <NodeCard
                key={node.id}
                node={node}
                isCritical={criticalPathSet.has(node.id)}
                isSelected={selectedNodeId === node.id}
                onSelect={() => setSelectedNodeId(node.id)}
              />
            ))}
          </div>
        </div>

        {/* Lane 3: Post-Commissioning */}
        <div className="space-y-4">
          <div className="p-3.5 bg-amber-950/30 border border-amber-800/40 rounded-xl">
            <span className="text-[10px] font-mono font-bold text-amber-400 uppercase tracking-wider block">
              Stage 3
            </span>
            <h3 className="text-sm font-bold text-white">Post-Commissioning Licenses</h3>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Final statutory operating licenses prior to commercial sales & dispatch.
            </p>
          </div>

          <div className="space-y-3">
            {postCommissioningNodes.map((node) => (
              <NodeCard
                key={node.id}
                node={node}
                isCritical={criticalPathSet.has(node.id)}
                isSelected={selectedNodeId === node.id}
                onSelect={() => setSelectedNodeId(node.id)}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function NodeCard({
  node,
  isCritical,
  isSelected,
  onSelect,
}: {
  node: GraphNode;
  isCritical: boolean;
  isSelected: boolean;
  onSelect: () => void;
}) {
  return (
    <div
      onClick={onSelect}
      className={`p-4 rounded-xl border transition-all cursor-pointer select-none relative backdrop-blur-sm ${
        isSelected
          ? "ring-2 ring-indigo-500 bg-slate-900 border-indigo-400"
          : isCritical
          ? "bg-slate-900/90 border-amber-500/60 shadow-lg shadow-amber-500/10"
          : "bg-slate-900/70 border-slate-800 hover:border-slate-700"
      }`}
    >
      {/* Critical Path Badge */}
      {isCritical && (
        <span className="absolute -top-2.5 right-3 text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-500 text-slate-950 shadow-sm">
          ★ Critical Path
        </span>
      )}

      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-bold border border-slate-700">
          {node.id}
        </span>
        <span className="text-[11px] text-slate-400 font-mono">
          {node.department_code}
        </span>
      </div>

      <h4 className="text-xs font-bold text-white mb-2 leading-snug line-clamp-2">
        {node.title}
      </h4>

      {/* Unlock & Readiness Pill */}
      <div className="mb-3">
        {node.status === "APPROVED" ? (
          <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-950/80 text-emerald-300 border border-emerald-700/50">
            ✓ Clearance Approved
          </span>
        ) : node.is_unlocked ? (
          <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-700/50">
            ● Ready to Apply
          </span>
        ) : (
          <span className="inline-flex items-center text-[10px] font-semibold px-2 py-0.5 rounded bg-rose-950/80 text-rose-300 border border-rose-800/40">
            🔒 Blocked: Needs {node.missing_prerequisites.join(", ")}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between pt-2 border-t border-slate-800/80 text-[11px]">
        <span className="text-slate-400">{node.sla_days} Days SLA</span>
        <span className="font-bold text-emerald-400">
          ₹{node.estimated_fee.toLocaleString("en-IN")}
        </span>
      </div>
    </div>
  );
}

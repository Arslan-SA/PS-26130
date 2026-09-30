"use client";

import React, { useState } from "react";
import { ApprovalChecklist, ChecklistItem } from "@/lib/approvals";

interface Props {
  checklist: ApprovalChecklist;
}

export default function ApprovalChecklistView({ checklist }: Props) {
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({});

  const toggleCheck = (id: string) => {
    setCheckedItems((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const filteredItems = checklist.items.filter((item) => {
    if (selectedCategory === "ALL") return true;
    return item.category === selectedCategory;
  });

  const completedCount = checklist.items.filter((it) => checkedItems[it.item_id]).length;
  const progressPercent = Math.round((completedCount / (checklist.items.length || 1)) * 100);

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case "FORM":
        return "bg-purple-950/80 text-purple-300 border-purple-800/40";
      case "DOCUMENT":
        return "bg-blue-950/80 text-blue-300 border-blue-800/40";
      case "PREREQUISITE":
        return "bg-amber-950/80 text-amber-300 border-amber-800/40";
      case "INSPECTION":
        return "bg-emerald-950/80 text-emerald-300 border-emerald-800/40";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-800 pb-5">
        <div>
          <span className="font-mono text-xs px-2.5 py-0.5 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-800/40 font-semibold tracking-wider">
            {checklist.approval_code} DOSSIER CHECKLIST
          </span>
          <h2 className="text-xl font-bold text-white mt-1.5">{checklist.approval_title}</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            {checklist.issuing_authority} • <span className="italic">{checklist.statutory_act}</span>
          </p>
        </div>

        {/* Readiness Meter */}
        <div className="sm:text-right min-w-[180px]">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <span className="text-slate-400">Document Readiness:</span>
            <span className="font-bold text-indigo-400">{progressPercent}%</span>
          </div>
          <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700/60">
            <div
              className="bg-indigo-500 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progressPercent}%` }}
            ></div>
          </div>
          <span className="text-[11px] text-slate-500 mt-1 block">
            {completedCount} of {checklist.items.length} items verified ready
          </span>
        </div>
      </div>

      {/* Category Filter Tabs */}
      <div className="flex flex-wrap gap-2">
        {[
          { id: "ALL", label: `All Requirements (${checklist.items.length})` },
          {
            id: "DOCUMENT",
            label: `Technical Documents (${
              checklist.items.filter((i) => i.category === "DOCUMENT").length
            })`,
          },
          {
            id: "FORM",
            label: `Statutory Forms (${
              checklist.items.filter((i) => i.category === "FORM").length
            })`,
          },
          {
            id: "PREREQUISITE",
            label: `Prerequisites (${
              checklist.items.filter((i) => i.category === "PREREQUISITE").length
            })`,
          },
          {
            id: "INSPECTION",
            label: `Inspection Checks (${
              checklist.items.filter((i) => i.category === "INSPECTION").length
            })`,
          },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setSelectedCategory(tab.id)}
            className={`text-xs font-semibold px-3 py-1.5 rounded-lg transition-all ${
              selectedCategory === tab.id
                ? "bg-indigo-600 text-white shadow-sm"
                : "bg-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-700 border border-slate-700/60"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Checklist Items */}
      <div className="space-y-3">
        {filteredItems.map((item) => {
          const isChecked = !!checkedItems[item.item_id];
          return (
            <div
              key={item.item_id}
              onClick={() => toggleCheck(item.item_id)}
              className={`flex items-start gap-4 p-4 rounded-xl border transition-all cursor-pointer select-none ${
                isChecked
                  ? "bg-indigo-950/20 border-indigo-700/50"
                  : "bg-slate-950/40 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900/50"
              }`}
            >
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => {}} // handled by div click
                className="mt-1 h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
              />

              <div className="flex-1">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded border uppercase tracking-wider ${getCategoryBadge(
                      item.category
                    )}`}
                  >
                    {item.category}
                  </span>
                  {item.is_mandatory && (
                    <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/40">
                      Mandatory
                    </span>
                  )}
                  <span className="font-mono text-xs text-slate-500">[{item.item_id}]</span>
                </div>

                <h4
                  className={`text-sm font-semibold transition-colors ${
                    isChecked ? "text-slate-300 line-through decoration-slate-500" : "text-white"
                  }`}
                >
                  {item.title}
                </h4>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{item.description}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

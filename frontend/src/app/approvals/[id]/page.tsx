"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import {
  ApprovalChecklist,
  ApprovalRequirement,
  RequirementStage,
  RequirementStatus,
  getRequirementById,
  getRequirementChecklist,
  updateRequirementStatus,
} from "@/lib/approvals";
import ApprovalChecklistView from "@/components/approvals/ApprovalChecklistView";

export default function ApprovalDetailPage() {
  const params = useParams();
  const requirementId = params?.id as string;

  const [requirement, setRequirement] = useState<ApprovalRequirement | null>(null);
  const [checklist, setChecklist] = useState<ApprovalChecklist | null>(null);
  const [activeTab, setActiveTab] = useState<"CHECKLIST" | "LEGAL" | "WORKFLOW" | "CONTACT">("CHECKLIST");
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [updating, setUpdating] = useState<boolean>(false);

  useEffect(() => {
    async function loadDetail() {
      if (!requirementId) return;
      try {
        setLoading(true);
        const req = await getRequirementById(requirementId);
        setRequirement(req);

        try {
          const chk = await getRequirementChecklist(requirementId);
          setChecklist(chk);
        } catch (e) {
          console.warn("No specific checklist found for this clearance", e);
        }
      } catch (err: any) {
        console.error("Failed to load approval detail:", err);
        setErrorMsg(err.message || "Failed to load approval requirement.");
      } finally {
        setLoading(false);
      }
    }
    loadDetail();
  }, [requirementId]);

  const handleStatusChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newStatus = e.target.value as RequirementStatus;
    if (!requirement) return;
    try {
      setUpdating(true);
      const updated = await updateRequirementStatus(requirement.id, newStatus);
      setRequirement(updated);
    } catch (err: any) {
      console.error("Status update failed:", err);
    } finally {
      setUpdating(false);
    }
  };

  const getStageBadge = (stage: RequirementStage) => {
    switch (stage) {
      case "PRE_ESTABLISHMENT":
        return "bg-emerald-950/80 text-emerald-300 border-emerald-700/50";
      case "PRE_COMMISSIONING":
        return "bg-blue-950/80 text-blue-300 border-blue-700/50";
      case "POST_COMMISSIONING":
        return "bg-amber-950/80 text-amber-300 border-amber-700/50";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  return (
    <ProtectedRoute allowedRoles={["INDUSTRY_USER", "DEPARTMENT_OFFICER", "ADMIN"]}>
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto space-y-6">
          {/* Back Navigation */}
          <div>
            <Link
              href="/approvals"
              className="inline-flex items-center text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              ← Back to Clearances Roadmap
            </Link>
          </div>

          {loading ? (
            <div className="p-16 text-center text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800">
              <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-slate-700 border-t-indigo-500 mb-4"></div>
              <p className="text-sm">Loading clearance specifications and statutory checklist...</p>
            </div>
          ) : errorMsg || !requirement ? (
            <div className="p-8 rounded-2xl bg-rose-950/40 border border-rose-800/60 text-rose-300">
              <h3 className="font-bold text-base mb-1">Clearance Record Unavailable</h3>
              <p className="text-xs">{errorMsg || "Requirement could not be found."}</p>
            </div>
          ) : (
            <>
              {/* Hero Clearance Banner */}
              <div className="p-6 sm:p-8 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md space-y-6">
                <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs px-2.5 py-0.5 rounded bg-indigo-950/80 text-indigo-300 border border-indigo-700/50 font-semibold tracking-wider">
                        {requirement.approval?.code || "REQ"}
                      </span>
                      <span
                        className={`text-xs px-2.5 py-0.5 rounded-full font-medium border ${getStageBadge(
                          requirement.stage
                        )}`}
                      >
                        {requirement.stage.replace("_", " ")}
                      </span>
                      {requirement.is_mandatory ? (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-rose-950/60 text-rose-300 border border-rose-800/40">
                          Mandatory Statutory Clearance
                        </span>
                      ) : (
                        <span className="text-xs font-medium px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                          Conditional
                        </span>
                      )}
                    </div>

                    <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                      {requirement.approval?.title || requirement.approval_id}
                    </h1>

                    <p className="text-sm text-slate-400">
                      Issuing Authority:{" "}
                      <span className="text-white font-medium">
                        {requirement.approval?.issuing_authority || requirement.approval?.department_code}
                      </span>
                      {requirement.approval?.statutory_act && (
                        <>
                          <span className="mx-2">•</span>
                          <span className="text-slate-300 italic font-normal">
                            {requirement.approval.statutory_act}
                          </span>
                        </>
                      )}
                    </p>
                  </div>

                  {/* Status Dropdown */}
                  <div className="bg-slate-950/60 border border-slate-800 p-4 rounded-xl space-y-2 min-w-[200px]">
                    <label htmlFor="compliance-status-select" className="text-xs font-medium text-slate-400 block">Compliance Status</label>
                    <select
                      id="compliance-status-select"
                      value={requirement.status}
                      disabled={updating}
                      onChange={handleStatusChange}
                      aria-label="Compliance Status"
                      className="w-full text-xs font-semibold px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white focus:ring-2 focus:ring-indigo-500 outline-none"
                    >
                      <option value="NOT_STARTED">Not Started</option>
                      <option value="IN_PROGRESS">In Progress (Dossier Drafting)</option>
                      <option value="SUBMITTED">Submitted on Single Window</option>
                      <option value="UNDER_REVIEW">Under Departmental Review</option>
                      <option value="APPROVED">Granted / Approved</option>
                      <option value="EXEMPTED">Exempted</option>
                    </select>
                  </div>
                </div>

                {/* Key Stat Cards */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-800/80">
                  <div className="p-3.5 bg-slate-950/40 rounded-xl border border-slate-800/60">
                    <span className="text-[11px] text-slate-400 block">SLA Turnaround</span>
                    <span className="text-lg font-bold text-white">
                      {requirement.sla_deadline_days} Days
                    </span>
                  </div>
                  <div className="p-3.5 bg-slate-950/40 rounded-xl border border-slate-800/60">
                    <span className="text-[11px] text-slate-400 block">Statutory Base Fee</span>
                    <span className="text-lg font-bold text-emerald-400">
                      ₹{requirement.estimated_fee.toLocaleString("en-IN")}
                    </span>
                  </div>
                  <div className="p-3.5 bg-slate-950/40 rounded-xl border border-slate-800/60">
                    <span className="text-[11px] text-slate-400 block">Validity Period</span>
                    <span className="text-lg font-bold text-indigo-400">
                      {requirement.approval?.validity_period_months
                        ? `${requirement.approval.validity_period_months} Months`
                        : "Perpetual"}
                    </span>
                  </div>
                  <div className="p-3.5 bg-slate-950/40 rounded-xl border border-slate-800/60">
                    <span className="text-[11px] text-slate-400 block">Priority Rank</span>
                    <span className="text-lg font-bold text-amber-400">
                      Tier {requirement.priority}
                    </span>
                  </div>
                </div>

                {/* Statutory Trigger Justification Banner */}
                <div className="p-4 rounded-xl bg-indigo-950/30 border border-indigo-900/50 text-xs text-indigo-200 leading-relaxed">
                  <span className="font-semibold text-indigo-300 block mb-1">
                    Regulatory Mandate for Your Enterprise:
                  </span>
                  {requirement.trigger_reason}
                </div>
              </div>

              {/* Navigation Tabs */}
              <div className="flex border-b border-slate-800 gap-4">
                {[
                  { id: "CHECKLIST", label: "Dossier Checklist & Documents" },
                  { id: "LEGAL", label: "Statutory Scope & Legal Authority" },
                  { id: "WORKFLOW", label: "Single-Window Workflow Steps" },
                  { id: "CONTACT", label: "Department & Grievance Desk" },
                ].map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`pb-3 text-xs font-semibold transition-all border-b-2 ${
                      activeTab === tab.id
                        ? "border-indigo-500 text-indigo-400"
                        : "border-transparent text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab Content 1: Checklist */}
              {activeTab === "CHECKLIST" && (
                <div>
                  {checklist ? (
                    <ApprovalChecklistView checklist={checklist} />
                  ) : (
                    <div className="p-12 text-center bg-slate-900/40 rounded-2xl border border-slate-800 text-slate-400">
                      Standard dossier checklist is being populated by departmental officers.
                    </div>
                  )}
                </div>
              )}

              {/* Tab Content 2: Legal Scope */}
              {activeTab === "LEGAL" && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
                  <h3 className="text-lg font-bold text-white">Statutory Governing Framework</h3>
                  <div className="space-y-4 text-xs text-slate-300 leading-relaxed">
                    <p>
                      This statutory clearance is governed under the{" "}
                      <strong className="text-white font-semibold">
                        {requirement.approval?.statutory_act || "relevant industrial enactment"}
                      </strong>
                      . Operating an industrial establishment without obtaining this prior approval constitutes a cognizable offense punishable under statutory penalty provisions.
                    </p>

                    <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-800/40 text-amber-200 space-y-1">
                      <span className="font-semibold block text-amber-300">Statutory Notice:</span>
                      <p>
                        Civil construction, trial operations, or commercial energization undertaken without a valid clearance order may lead to immediate stop-work orders, disconnection of power/water utilities, and financial penalties.
                      </p>
                    </div>

                    <h4 className="text-sm font-semibold text-white pt-2">Detailed Scope Description:</h4>
                    <p>{requirement.approval?.description || "Refer to department guidelines for detailed legal provisions."}</p>
                  </div>
                </div>
              )}

              {/* Tab Content 3: Workflow */}
              {activeTab === "WORKFLOW" && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
                  <h3 className="text-lg font-bold text-white">Application Procedure & Turnaround Roadmap</h3>
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {[
                      {
                        step: "Step 01",
                        title: "Dossier Compilation",
                        desc: "Gather architectural site plans, equipment schedules, and statutory certificates as listed in the checklist.",
                      },
                      {
                        step: "Step 02",
                        title: "Treasury Fee Deposit",
                        desc: `Calculate statutory fee (₹${requirement.estimated_fee.toLocaleString(
                          "en-IN"
                        )}) and remit payment via State Integrated Financial System.`,
                      },
                      {
                        step: "Step 03",
                        title: "Departmental Inspection",
                        desc: `Competent officers conduct on-site verification within ${Math.round(
                          requirement.sla_deadline_days * 0.6
                        )} days of valid submission.`,
                      },
                      {
                        step: "Step 04",
                        title: "Statutory Order Grant",
                        desc: `Digitally signed approval certificate issued on the Single-Window portal before ${requirement.sla_deadline_days}-day SLA cutoff.`,
                      },
                    ].map((st, idx) => (
                      <div key={idx} className="p-4 bg-slate-950/50 border border-slate-800 rounded-xl space-y-2">
                        <span className="text-xs font-mono font-bold text-indigo-400">{st.step}</span>
                        <h4 className="text-sm font-bold text-white">{st.title}</h4>
                        <p className="text-xs text-slate-400 leading-relaxed">{st.desc}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tab Content 4: Contact & Grievance */}
              {activeTab === "CONTACT" && (
                <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 space-y-6">
                  <h3 className="text-lg font-bold text-white">Competent Authority & Public Service Guarantee Desk</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
                    <div className="p-4 bg-slate-950/50 border border-slate-800 rounded-xl space-y-2">
                      <span className="text-slate-400 block font-medium">Department Code</span>
                      <span className="text-base font-bold text-white font-mono">
                        {requirement.approval?.department_code || "REGULATORY"}
                      </span>
                    </div>

                    <div className="p-4 bg-slate-950/50 border border-slate-800 rounded-xl space-y-2">
                      <span className="text-slate-400 block font-medium">Statutory SLA Commitment</span>
                      <span className="text-base font-bold text-indigo-400">
                        {requirement.sla_deadline_days} Calendar Days Guarantee
                      </span>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-slate-950/30 border border-slate-800 text-xs text-slate-300">
                    <p>
                      Under the State Public Service Delivery Guarantee Act, if an application remains un-actioned beyond the statutory SLA deadline without a recorded deficiency query, the applicant may lodge a formal escalation through the state administrative grievance portal.
                    </p>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </ProtectedRoute>
  );
}

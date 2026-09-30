/**
 * Statutory Approvals and Clearance Requirements API client and types.
 */

import { apiFetch } from "./auth";

export type RequirementStatus =
  | "NOT_STARTED"
  | "IN_PROGRESS"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "EXEMPTED";

export type RequirementStage =
  | "PRE_ESTABLISHMENT"
  | "PRE_COMMISSIONING"
  | "POST_COMMISSIONING"
  | "REGULAR_OPERATIONS";

export interface Approval {
  id: string;
  code: string;
  title: string;
  department_code: string;
  issuing_authority: string;
  statutory_act?: string | null;
  validity_period_months?: number | null;
  is_mandatory: boolean;
  sla_days: number;
  estimated_fee_base: number;
  description?: string | null;
}

export interface ApprovalRequirement {
  id: string;
  business_id: string;
  approval_id: string;
  status: RequirementStatus;
  stage: RequirementStage;
  priority: number;
  is_mandatory: boolean;
  trigger_reason: string;
  estimated_fee: number;
  sla_deadline_days: number;
  notes?: string | null;
  created_at: string;
  updated_at: string;
  approval?: Approval | null;
}

export interface ClearanceSummary {
  business_id: string;
  total_requirements: number;
  mandatory_requirements: number;
  total_estimated_fee: number;
  pre_establishment_critical_days: number;
  by_stage: Record<string, number>;
  by_department: Record<string, number>;
  status_breakdown: Record<string, number>;
}

export interface DiscoveryResponse {
  business_id: string;
  count: number;
  requirements: ApprovalRequirement[];
  summary: ClearanceSummary;
}

/**
 * Execute automated statutory discovery engine for an enterprise unit.
 */
export async function discoverApprovals(businessId: string): Promise<DiscoveryResponse> {
  return apiFetch<DiscoveryResponse>(`/approvals/discover/${businessId}`, {
    method: "POST",
  });
}

/**
 * Retrieve active clearance requirements for an enterprise.
 */
export async function getBusinessRequirements(businessId: string): Promise<ApprovalRequirement[]> {
  return apiFetch<ApprovalRequirement[]>(`/approvals/business/${businessId}`);
}

/**
 * Retrieve consolidated clearance summary and fee metrics.
 */
export async function getClearanceSummary(businessId: string): Promise<ClearanceSummary> {
  return apiFetch<ClearanceSummary>(`/approvals/summary/${businessId}`);
}

/**
 * Update clearance requirement progress status or add notes.
 */
export async function updateRequirementStatus(
  requirementId: string,
  status: RequirementStatus,
  notes?: string
): Promise<ApprovalRequirement> {
  return apiFetch<ApprovalRequirement>(`/approvals/requirements/${requirementId}/status`, {
    method: "PATCH",
    body: JSON.stringify({ status, notes }),
  });
}

export interface ChecklistItem {
  item_id: string;
  title: string;
  category: "FORM" | "DOCUMENT" | "PREREQUISITE" | "INSPECTION";
  description: string;
  is_mandatory: boolean;
  template_url?: string | null;
}

export interface ApprovalChecklist {
  approval_code: string;
  approval_title: string;
  issuing_authority: string;
  statutory_act: string;
  items: ChecklistItem[];
}

/**
 * Retrieve statutory prerequisite checklist by approval code.
 */
export async function getApprovalChecklist(approvalCode: string): Promise<ApprovalChecklist> {
  return apiFetch<ApprovalChecklist>(`/approvals/${approvalCode}/checklist`);
}

/**
 * Retrieve statutory checklist for a specific requirement instance.
 */
export async function getRequirementChecklist(requirementId: string): Promise<ApprovalChecklist> {
  return apiFetch<ApprovalChecklist>(`/approvals/requirements/${requirementId}/checklist`);
}

/**
 * Retrieve an individual approval requirement by its ID.
 */
export async function getRequirementById(requirementId: string): Promise<ApprovalRequirement> {
  return apiFetch<ApprovalRequirement>(`/approvals/requirements/${requirementId}`);
}

export interface GraphNode {
  id: string;
  requirement_id: string;
  title: string;
  department_code: string;
  issuing_authority: string;
  stage: RequirementStage;
  status: RequirementStatus;
  is_unlocked: boolean;
  missing_prerequisites: string[];
  estimated_fee: number;
  sla_days: number;
  priority: number;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  dependency_type: string;
  description?: string | null;
}

export interface DependencyGraphResponse {
  business_id: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  topological_order: string[];
  critical_path: string[];
  critical_path_days: number;
}

/**
 * Retrieve the statutory clearance dependency DAG for an enterprise.
 */
export async function getDependencyGraph(businessId: string): Promise<DependencyGraphResponse> {
  return apiFetch<DependencyGraphResponse>(`/approvals/graph/${businessId}`);
}




/**
 * Compliance & Monitoring API client and TypeScript definitions (Phase 7).
 * Provides typed interfaces and API functions for compliance dashboard,
 * alerts, status, prioritized queue, and filing operations.
 */

import { apiFetch } from "./auth";

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export type ComplianceCategory =
  | "ENVIRONMENTAL"
  | "LABOR"
  | "FIRE_SAFETY"
  | "FACTORY_OPERATIONS"
  | "BOILER_PRESSURE"
  | "ELECTRICAL"
  | "TAX_STATUTORY"
  | "LAND_ZONING"
  | "OTHER";

export type ComplianceFrequency =
  | "ONE_TIME"
  | "MONTHLY"
  | "QUARTERLY"
  | "HALF_YEARLY"
  | "ANNUAL"
  | "BIENNIAL"
  | "QUINQUENNIAL"
  | "EVENT_DRIVEN";

export type CompliancePriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export type ComplianceRecordStatus =
  | "UPCOMING"
  | "DUE_SOON"
  | "OVERDUE"
  | "IN_PROGRESS"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "APPROVED"
  | "REJECTED"
  | "EXEMPTED"
  | "EXPIRED";

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

export interface ComplianceRequirement {
  id: string;
  approval_id: string;
  code: string;
  title: string;
  description?: string | null;
  category: ComplianceCategory;
  frequency: ComplianceFrequency;
  frequency_months: number;
  priority: CompliancePriority;
  warning_days: number;
  statutory_act?: string | null;
  penalty_description?: string | null;
  penalty_amount_max: number;
  required_documents: string[];
  applicable_pollution_categories: string[];
  applicable_industry_scales: string[];
  is_mandatory: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ComplianceRecordSummary {
  id: string;
  business_id: string;
  requirement_id: string;
  status: ComplianceRecordStatus;
  cycle_label: string;
  due_date: string;
  days_overdue: number;
  requirement_code?: string | null;
  requirement_title?: string | null;
  requirement_category?: ComplianceCategory | null;
  requirement_priority?: CompliancePriority | null;
  penalty_imposed: number;
  created_at: string;
}

export interface ComplianceRecordDetail extends ComplianceRecordSummary {
  application_id?: string | null;
  warning_date?: string | null;
  submitted_at?: string | null;
  approved_at?: string | null;
  new_valid_until?: string | null;
  evidence_document_ids: string[];
  filing_data: Record<string, unknown>;
  remarks?: string | null;
  officer_remarks?: string | null;
  responsible_user_id?: string | null;
  is_active: boolean;
  updated_at: string;
  requirement_frequency?: ComplianceFrequency | null;
  business_name?: string | null;
}

export interface ComplianceDashboardMetrics {
  business_id: string;
  total_obligations: number;
  compliant_count: number;
  due_soon_count: number;
  overdue_count: number;
  in_progress_count: number;
  submitted_count: number;
  exempted_count: number;
  expired_count: number;
  compliance_rate_percent: number;
  total_penalty_exposure: number;
  total_penalties_imposed: number;
  next_deadline?: string | null;
  most_critical_item?: string | null;
}

export interface ComplianceAlert {
  id: string;
  record_id: string;
  requirement_code: string;
  requirement_title: string;
  category: ComplianceCategory;
  priority: CompliancePriority;
  alert_type: string;
  message: string;
  due_date: string;
  days_remaining: number;
  penalty_exposure: number;
  business_id: string;
  business_name?: string | null;
}

export interface CompliancePrioritizedItem {
  rank: number;
  record_id: string;
  requirement_code: string;
  requirement_title: string;
  category: ComplianceCategory;
  priority: CompliancePriority;
  status: ComplianceRecordStatus;
  due_date: string;
  days_remaining: number;
  penalty_exposure: number;
  urgency_score: number;
  recommended_action: string;
  business_id: string;
}

export interface ComplianceStatusSummary {
  category: ComplianceCategory;
  total: number;
  compliant: number;
  due_soon: number;
  overdue: number;
  expired: number;
  compliance_rate_percent: number;
}

export interface ComplianceStatusResponse {
  business_id: string;
  overall_compliance_rate: number;
  overall_health: string;
  category_breakdown: ComplianceStatusSummary[];
  recent_deadlines: ComplianceRecordSummary[];
  upcoming_deadlines: ComplianceRecordSummary[];
}

// ---------------------------------------------------------------------------
// API Functions
// ---------------------------------------------------------------------------

export async function fetchComplianceDashboard(
  businessId: string
): Promise<ComplianceDashboardMetrics> {
  return apiFetch(`/compliance/businesses/${businessId}/dashboard`);
}

export async function fetchComplianceAlerts(
  businessId: string
): Promise<{ total: number; critical_count: number; high_count: number; items: ComplianceAlert[] }> {
  return apiFetch(`/compliance/businesses/${businessId}/alerts`);
}

export async function fetchComplianceStatus(
  businessId: string
): Promise<ComplianceStatusResponse> {
  return apiFetch(`/compliance/businesses/${businessId}/status`);
}

export async function fetchCompliancePriorities(
  businessId: string,
  limit = 20
): Promise<{ total: number; items: CompliancePrioritizedItem[] }> {
  return apiFetch(`/compliance/businesses/${businessId}/priorities?limit=${limit}`);
}

export async function fetchComplianceRecords(
  businessId: string,
  params?: { status?: ComplianceRecordStatus; category?: ComplianceCategory; limit?: number; offset?: number }
): Promise<{ total: number; items: ComplianceRecordSummary[] }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.category) searchParams.set("category", params.category);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  const qs = searchParams.toString();
  return apiFetch(`/compliance/businesses/${businessId}/records${qs ? `?${qs}` : ""}`);
}

export async function fetchComplianceRecordDetail(
  recordId: string
): Promise<ComplianceRecordDetail> {
  return apiFetch(`/compliance/records/${recordId}`);
}

export async function submitComplianceFiling(
  recordId: string,
  payload: {
    filing_data: Record<string, unknown>;
    evidence_document_ids: string[];
    remarks?: string;
  }
): Promise<ComplianceRecordDetail> {
  return apiFetch(`/compliance/records/${recordId}/submit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function evaluateBusinessCompliance(
  businessId: string
): Promise<{ total: number; items: ComplianceRequirement[] }> {
  return apiFetch(`/compliance/businesses/${businessId}/evaluate`, {
    method: "POST",
  });
}

export async function generateComplianceRecords(
  businessId: string,
  cyclesAhead = 1
): Promise<{ total: number; items: ComplianceRecordSummary[] }> {
  return apiFetch(`/compliance/businesses/${businessId}/generate?cycles_ahead=${cyclesAhead}`, {
    method: "POST",
  });
}

export async function fetchComplianceRequirements(): Promise<{
  total: number;
  items: ComplianceRequirement[];
}> {
  return apiFetch(`/compliance/requirements`);
}

// ---------------------------------------------------------------------------
// Display Helpers
// ---------------------------------------------------------------------------

export const PRIORITY_COLORS: Record<CompliancePriority, string> = {
  CRITICAL: "#dc2626",
  HIGH: "#ea580c",
  MEDIUM: "#ca8a04",
  LOW: "#16a34a",
};

export const STATUS_COLORS: Record<ComplianceRecordStatus, string> = {
  UPCOMING: "#6b7280",
  DUE_SOON: "#f59e0b",
  OVERDUE: "#dc2626",
  IN_PROGRESS: "#3b82f6",
  SUBMITTED: "#8b5cf6",
  UNDER_REVIEW: "#6366f1",
  APPROVED: "#16a34a",
  REJECTED: "#ef4444",
  EXEMPTED: "#64748b",
  EXPIRED: "#991b1b",
};

export const CATEGORY_LABELS: Record<ComplianceCategory, string> = {
  ENVIRONMENTAL: "Environmental",
  LABOR: "Labour & Welfare",
  FIRE_SAFETY: "Fire Safety",
  FACTORY_OPERATIONS: "Factory Operations",
  BOILER_PRESSURE: "Boiler & Pressure",
  ELECTRICAL: "Electrical Safety",
  TAX_STATUTORY: "Tax & Statutory",
  LAND_ZONING: "Land & Zoning",
  OTHER: "Other",
};

export const CATEGORY_ICONS: Record<ComplianceCategory, string> = {
  ENVIRONMENTAL: "🌿",
  LABOR: "👷",
  FIRE_SAFETY: "🔥",
  FACTORY_OPERATIONS: "🏭",
  BOILER_PRESSURE: "♨️",
  ELECTRICAL: "⚡",
  TAX_STATUTORY: "📊",
  LAND_ZONING: "🏗️",
  OTHER: "📋",
};

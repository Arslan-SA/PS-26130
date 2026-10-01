/**
 * Statutory Clearance Applications API client and TypeScript definitions (Phase 6).
 */

import { apiFetch } from "./auth";

export type ApplicationStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "UNDER_REVIEW"
  | "QUERY_RAISED"
  | "RESUBMITTED"
  | "INSPECTION_SCHEDULED"
  | "INSPECTION_COMPLETED"
  | "APPROVED"
  | "REJECTED"
  | "WITHDRAWN";

export type QueryStatus = "OPEN" | "RESOLVED" | "WAIVED";

export type InspectionStatus = "SCHEDULED" | "IN_PROGRESS" | "COMPLETED" | "CANCELLED";

export type InspectionRecommendation = "SATISFACTORY" | "NON_COMPLIANT" | "REMEDIATION_REQUIRED";

export interface ApplicationStatusHistory {
  id: string;
  application_id: string;
  from_status?: ApplicationStatus | null;
  to_status: ApplicationStatus;
  changed_by_user_id?: string | null;
  changed_by_name?: string | null;
  action: string;
  remarks?: string | null;
  created_at: string;
}

export interface ApplicationQuery {
  id: string;
  application_id: string;
  raised_by_user_id?: string | null;
  raised_by_name?: string | null;
  document_id?: string | null;
  query_title: string;
  query_text: string;
  status: QueryStatus;
  due_date?: string | null;
  response_text?: string | null;
  response_document_id?: string | null;
  resolved_at?: string | null;
  created_at: string;
}

export interface Inspection {
  id: string;
  application_id: string;
  inspector_id?: string | null;
  inspector_name?: string | null;
  department_id?: string | null;
  scheduled_date: string;
  status: InspectionStatus;
  instructions?: string | null;
  findings?: string | null;
  checklist_results: Record<string, any>;
  recommendation?: InspectionRecommendation | null;
  geo_latitude?: number | null;
  geo_longitude?: number | null;
  report_document_id?: string | null;
  completed_at?: string | null;
  created_at: string;
}

export interface ApplicationSummary {
  id: string;
  application_number: string;
  business_id: string;
  business_name?: string | null;
  approval_id: string;
  approval_code?: string | null;
  approval_title?: string | null;
  department_code: string;
  department_name?: string | null;
  status: ApplicationStatus;
  fee_amount: number;
  fee_paid: boolean;
  submitted_at?: string | null;
  sla_due_date?: string | null;
  sla_days_remaining?: number | null;
  approval_certificate_number?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationDetail extends ApplicationSummary {
  requirement_id?: string | null;
  department_id?: string | null;
  applied_by_user_id: string;
  applied_by_name?: string | null;
  assigned_officer_id?: string | null;
  assigned_officer_name?: string | null;
  application_data: Record<string, any>;
  attached_document_ids: string[];
  fee_reference?: string | null;
  reviewed_at?: string | null;
  decided_at?: string | null;
  rejection_reason?: string | null;
  validity_years?: number | null;
  certificate_valid_until?: string | null;
  status_history: ApplicationStatusHistory[];
  queries: ApplicationQuery[];
  inspections: Inspection[];
}

export interface OfficerInboxMetrics {
  pending_scrutiny: number;
  under_review: number;
  queries_pending_applicant_response: number;
  inspections_scheduled: number;
  approved_count: number;
  rejected_count: number;
  sla_critical_count: number;
  sla_compliance_rate_percent: number;
}

export interface OfficerInboxSummary {
  officer_id: string;
  full_name: string;
  department_id?: string | null;
  department_code: string;
  designation?: string | null;
  role: string;
  queue_metrics: OfficerInboxMetrics;
  next_action: string;
}

export interface ApplicationCreatePayload {
  business_id: string;
  approval_id: string;
  requirement_id?: string;
  application_data?: Record<string, any>;
  attached_document_ids?: string[];
  fee_amount?: number;
  fee_paid?: boolean;
  fee_reference?: string;
}

export interface ApplicationSubmitPayload {
  fee_paid: boolean;
  fee_reference: string;
  additional_remarks?: string;
}

export interface QueryRespondPayload {
  response_text: string;
  response_document_id?: string;
}

export interface QueryCreatePayload {
  document_id?: string;
  query_title: string;
  query_text: string;
  due_date?: string;
}

export interface ScheduleInspectionPayload {
  inspector_id: string;
  scheduled_date: string;
  instructions?: string;
}

export interface DetermineApplicationPayload {
  decision: "APPROVED" | "REJECTED";
  remarks?: string;
  rejection_reason?: string;
  validity_years?: number;
}

/**
 * List applications with optional query params.
 */
export async function getApplications(params?: {
  business_id?: string;
  department_code?: string;
  status?: ApplicationStatus;
}): Promise<ApplicationSummary[]> {
  const query = new URLSearchParams();
  if (params?.business_id) query.append("business_id", params.business_id);
  if (params?.department_code) query.append("department_code", params.department_code);
  if (params?.status) query.append("status", params.status);

  const qs = query.toString();
  return apiFetch<ApplicationSummary[]>(`/applications${qs ? `?${qs}` : ""}`);
}

/**
 * Get comprehensive application detail.
 */
export async function getApplicationDetail(id: string): Promise<ApplicationDetail> {
  return apiFetch<ApplicationDetail>(`/applications/${id}`);
}

/**
 * Create a new draft clearance application.
 */
export async function createApplication(payload: ApplicationCreatePayload): Promise<ApplicationDetail> {
  return apiFetch<ApplicationDetail>("/applications", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Formally submit a draft application with fee details.
 */
export async function submitApplication(
  id: string,
  payload: ApplicationSubmitPayload
): Promise<ApplicationDetail> {
  return apiFetch<ApplicationDetail>(`/applications/${id}/submit`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Respond to an open deficiency query.
 */
export async function respondToQuery(
  id: string,
  queryId: string,
  payload: QueryRespondPayload
): Promise<ApplicationQuery> {
  return apiFetch<ApplicationQuery>(`/applications/${id}/queries/${queryId}/respond`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Resubmit application after resolving all queries.
 */
export async function resubmitApplication(id: string, remarks?: string): Promise<ApplicationDetail> {
  const query = remarks ? `?remarks=${encodeURIComponent(remarks)}` : "";
  return apiFetch<ApplicationDetail>(`/applications/${id}/resubmit${query}`, {
    method: "POST",
  });
}

/**
 * Fetch officer department review dashboard & metrics.
 */
export async function getOfficerInboxSummary(): Promise<OfficerInboxSummary> {
  return apiFetch<OfficerInboxSummary>("/officer/inbox-summary");
}

/**
 * Fetch officer queue applications.
 */
export async function getOfficerApplications(status?: ApplicationStatus): Promise<ApplicationSummary[]> {
  const query = status ? `?status=${status}` : "";
  return apiFetch<ApplicationSummary[]>(`/officer/applications${query}`);
}

/**
 * Commence officer review on application.
 */
export async function startOfficerReview(id: string): Promise<ApplicationDetail> {
  return apiFetch<ApplicationDetail>(`/officer/applications/${id}/review`, {
    method: "POST",
  });
}

/**
 * Issue deficiency query as officer.
 */
export async function raiseOfficerQuery(
  id: string,
  payload: QueryCreatePayload
): Promise<ApplicationQuery> {
  return apiFetch<ApplicationQuery>(`/officer/applications/${id}/queries`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Schedule site inspection as officer.
 */
export async function scheduleInspection(
  id: string,
  payload: ScheduleInspectionPayload
): Promise<Inspection> {
  return apiFetch<Inspection>(`/officer/applications/${id}/schedule-inspection`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Render final statutory clearance determination (Approve/Reject).
 */
export async function determineApplication(
  id: string,
  payload: DetermineApplicationPayload
): Promise<ApplicationDetail> {
  return apiFetch<ApplicationDetail>(`/officer/applications/${id}/determine`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Government Schemes & Subsidies API client and TypeScript definitions (Phase 8).
 * Provides typed interfaces, API client functions, and display helpers for
 * Scheme Discovery, Eligibility Matching, Document Gap Analysis, and Application Tracking.
 */

import { apiFetch } from "./auth";

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export type SchemeType =
  | "CAPITAL_SUBSIDY"
  | "INTEREST_SUBVENTION"
  | "CREDIT_GUARANTEE"
  | "PRODUCTION_LINKED_INCENTIVE"
  | "QUALITY_CERTIFICATION"
  | "TECHNOLOGY_UPGRADATION"
  | "INFRASTRUCTURE_SUPPORT"
  | "GREEN_INCENTIVE"
  | "EXPORT_PROMOTION";

export type SchemeLevel = "CENTRAL" | "STATE";

export type ApplicationMode = "ONLINE" | "OFFLINE" | "HYBRID";

export type SchemeApplicationStatus =
  | "BOOKMARKED"
  | "PREPARING"
  | "APPLIED"
  | "UNDER_SCRUTINY"
  | "SANCTIONED"
  | "DISBURSED"
  | "REJECTED"
  | "CANCELLED";

// ---------------------------------------------------------------------------
// Interfaces
// ---------------------------------------------------------------------------

export interface GuidanceStep {
  step: number;
  title: string;
  instruction: string;
}

export interface SchemeEligibilityRule {
  id: string;
  scheme_id: string;
  min_investment?: number | null;
  max_investment?: number | null;
  min_turnover?: number | null;
  max_turnover?: number | null;
  allowed_msme_categories: string[];
  allowed_entity_types: string[];
  allowed_sectors_nic: string[];
  allowed_pollution_categories: string[];
  allowed_states: string[];
  requires_udyam: boolean;
  requires_women_ownership: boolean;
  min_employees?: number | null;
  max_firm_age_years?: number | null;
  min_score_threshold: number;
}

export interface GovernmentScheme {
  id: string;
  code: string;
  name: string;
  short_name: string;
  ministry: string;
  nodal_agency: string;
  scheme_type: SchemeType;
  level: SchemeLevel;
  state?: string | null;
  target_beneficiary: string;
  benefit_description: string;
  max_subsidy_amount?: number | null;
  subsidy_percentage?: number | null;
  interest_subsidy_rate?: number | null;
  official_portal_url?: string | null;
  application_mode: ApplicationMode;
  guidance_steps: GuidanceStep[];
  required_document_codes: string[];
  tags: string[];
  rule?: SchemeEligibilityRule | null;
  is_active: boolean;
}

export interface CriterionResult {
  name: string;
  status: "PASS" | "FAIL" | "WARNING" | "NOT_APPLICABLE";
  score_weight: number;
  earned_score: number;
  required_val: string;
  actual_val: string;
  explanation: string;
  is_hard_criterion: boolean;
}

export interface DocumentChecklistItem {
  code: string;
  title: string;
  is_available: boolean;
  document_id?: string | null;
  file_name?: string | null;
  verification_status?: string | null;
  is_verified: boolean;
}

export interface DocumentGapAnalysis {
  scheme_id: string;
  scheme_code: string;
  total_required: number;
  total_available: number;
  missing_count: number;
  readiness_percentage: number;
  documents: DocumentChecklistItem[];
}

export interface SchemeEvaluationResult {
  scheme_id: string;
  scheme_code: string;
  scheme_name: string;
  short_name: string;
  ministry: string;
  nodal_agency: string;
  scheme_type: SchemeType;
  level: SchemeLevel;
  match_score: number;
  is_eligible: boolean;
  max_subsidy_amount?: number | null;
  subsidy_percentage?: number | null;
  interest_subsidy_rate?: number | null;
  estimated_subsidy_amount?: number | null;
  criteria_breakdown: CriterionResult[];
  matching_criteria: string[];
  unmet_criteria: string[];
  recommendations: string[];
  official_portal_url?: string | null;
  tags: string[];
  required_document_codes: string[];
  guidance_steps: GuidanceStep[];
  document_readiness?: DocumentGapAnalysis;
}

export interface BusinessSchemeSummary {
  business_id: string;
  total_schemes_evaluated: number;
  total_eligible_schemes: number;
  total_subsidy_potential_inr: number;
  schemes: SchemeEvaluationResult[];
}

export interface SchemeApplication {
  id: string;
  business_id: string;
  scheme_id: string;
  status: SchemeApplicationStatus;
  match_score: number;
  applied_date?: string | null;
  sanctioned_amount?: number | null;
  application_reference_number?: string | null;
  notes?: string | null;
  missing_documents: string[];
  scheme_code?: string;
  scheme_name?: string;
  ministry?: string;
  max_subsidy_amount?: number | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Display Helper Functions
// ---------------------------------------------------------------------------

export function formatINR(amount?: number | null): string {
  if (amount === undefined || amount === null) return "N/A";
  if (amount >= 10000000) {
    const cr = amount / 10000000;
    return `₹${cr.toFixed(cr % 1 === 0 ? 0 : 2)} Cr`;
  }
  if (amount >= 100000) {
    const lk = amount / 100000;
    return `₹${lk.toFixed(lk % 1 === 0 ? 0 : 1)} Lakhs`;
  }
  return `₹${amount.toLocaleString("en-IN")}`;
}

export function getSchemeTypeLabel(type: SchemeType): string {
  switch (type) {
    case "CAPITAL_SUBSIDY":
      return "Capital Subsidy";
    case "INTEREST_SUBVENTION":
      return "Interest Subvention";
    case "CREDIT_GUARANTEE":
      return "Credit Guarantee";
    case "PRODUCTION_LINKED_INCENTIVE":
      return "PLI Incentive";
    case "QUALITY_CERTIFICATION":
      return "Quality (ZED) Subsidy";
    case "TECHNOLOGY_UPGRADATION":
      return "Technology Upgrade";
    case "INFRASTRUCTURE_SUPPORT":
      return "Infrastructure Support";
    case "GREEN_INCENTIVE":
      return "Green & Clean Tech";
    case "EXPORT_PROMOTION":
      return "Export Promotion";
    default:
      return type;
  }
}

export function getSchemeTypeBadge(type: SchemeType): {
  bg: string;
  text: string;
  border: string;
} {
  switch (type) {
    case "CAPITAL_SUBSIDY":
      return { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/30" };
    case "INTEREST_SUBVENTION":
      return { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/30" };
    case "CREDIT_GUARANTEE":
      return { bg: "bg-purple-500/10", text: "text-purple-400", border: "border-purple-500/30" };
    case "PRODUCTION_LINKED_INCENTIVE":
      return { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/30" };
    case "QUALITY_CERTIFICATION":
    case "GREEN_INCENTIVE":
      return { bg: "bg-teal-500/10", text: "text-teal-400", border: "border-teal-500/30" };
    case "TECHNOLOGY_UPGRADATION":
      return { bg: "bg-indigo-500/10", text: "text-indigo-400", border: "border-indigo-500/30" };
    default:
      return { bg: "bg-slate-500/10", text: "text-slate-400", border: "border-slate-500/30" };
  }
}

export function getApplicationStatusBadge(status: SchemeApplicationStatus): {
  bg: string;
  text: string;
  label: string;
} {
  switch (status) {
    case "BOOKMARKED":
      return { bg: "bg-slate-700 text-slate-300", text: "text-slate-300", label: "Bookmarked" };
    case "PREPARING":
      return { bg: "bg-amber-500/20 text-amber-300", text: "text-amber-400", label: "DPR In Preparation" };
    case "APPLIED":
      return { bg: "bg-blue-500/20 text-blue-300", text: "text-blue-400", label: "Applied Online" };
    case "UNDER_SCRUTINY":
      return { bg: "bg-indigo-500/20 text-indigo-300", text: "text-indigo-400", label: "Under Agency Scrutiny" };
    case "SANCTIONED":
      return { bg: "bg-emerald-500/20 text-emerald-300", text: "text-emerald-400", label: "Sanction Letter Issued" };
    case "DISBURSED":
      return { bg: "bg-teal-500/20 text-teal-300", text: "text-teal-400", label: "Disbursed to Bank" };
    case "REJECTED":
      return { bg: "bg-rose-500/20 text-rose-300", text: "text-rose-400", label: "Rejected" };
    default:
      return { bg: "bg-slate-700 text-slate-300", text: "text-slate-400", label: status };
  }
}

// ---------------------------------------------------------------------------
// API Client Functions
// ---------------------------------------------------------------------------

export async function fetchSchemeCatalog(params?: {
  type?: string;
  level?: string;
  search?: string;
}): Promise<GovernmentScheme[]> {
  const query = new URLSearchParams();
  if (params?.type) query.append("scheme_type", params.type);
  if (params?.level) query.append("level", params.level);
  if (params?.search) query.append("search", params.search);
  const qs = query.toString();
  return apiFetch<GovernmentScheme[]>(`/schemes/catalog${qs ? `?${qs}` : ""}`);
}

export async function fetchSchemeDetails(schemeId: string): Promise<GovernmentScheme> {
  return apiFetch<GovernmentScheme>(`/schemes/${schemeId}`);
}

export async function fetchBusinessRecommendations(
  businessId: string,
  schemeType?: string,
  minScore: number = 0.0
): Promise<BusinessSchemeSummary> {
  const query = new URLSearchParams();
  if (schemeType) query.append("scheme_type", schemeType);
  if (minScore > 0) query.append("min_score", minScore.toString());
  const qs = query.toString();
  return apiFetch<BusinessSchemeSummary>(`/schemes/recommendations/${businessId}${qs ? `?${qs}` : ""}`);
}

export async function evaluateSchemeForBusiness(
  schemeId: string,
  businessId: string
): Promise<SchemeEvaluationResult> {
  return apiFetch<SchemeEvaluationResult>(`/schemes/${schemeId}/evaluate/${businessId}`);
}

export async function trackSchemeApplication(
  businessId: string,
  schemeId: string,
  status: SchemeApplicationStatus = "BOOKMARKED",
  notes?: string,
  applicationReferenceNumber?: string
): Promise<SchemeApplication> {
  return apiFetch<SchemeApplication>("/schemes/applications", {
    method: "POST",
    body: JSON.stringify({
      business_id: businessId,
      scheme_id: schemeId,
      status,
      notes,
      application_reference_number: applicationReferenceNumber,
    }),
  });
}

export async function fetchBusinessSchemeApplications(
  businessId: string
): Promise<SchemeApplication[]> {
  return apiFetch<SchemeApplication[]>(`/schemes/applications/${businessId}`);
}

export async function updateSchemeApplication(
  applicationId: string,
  payload: {
    status?: SchemeApplicationStatus;
    notes?: string;
    sanctioned_amount?: number;
    application_reference_number?: string;
  }
): Promise<SchemeApplication> {
  return apiFetch<SchemeApplication>(`/schemes/applications/${applicationId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

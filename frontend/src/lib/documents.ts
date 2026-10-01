/**
 * Document API client library (Fragment 63).
 * Types and API helpers for document upload, listing, and metadata fetching.
 */

import { apiFetch } from "./auth";

export type DocumentType =
  | "PAN_CARD"
  | "GST_CERTIFICATE"
  | "UDYAM_REGISTRATION"
  | "LAND_DEED_OR_LEASE"
  | "SITE_PLAN_LAYOUT"
  | "PROJECT_REPORT_DPR"
  | "ENVIRONMENTAL_MANAGEMENT_PLAN"
  | "WATER_BALANCE_CHART"
  | "POWER_SANCTION_LETTER"
  | "FIRE_SAFETY_PLAN"
  | "FACTORY_BUILDING_PLAN"
  | "CERTIFICATE_OF_INCORPORATION"
  | "OTHER";

export type DocumentVerificationStatus =
  | "PENDING"
  | "PROCESSING"
  | "VERIFIED"
  | "FLAGGED"
  | "REJECTED";

export interface DocumentRecord {
  id: string;
  business_id: string;
  uploaded_by_user_id?: string | null;
  requirement_id?: string | null;
  document_type: DocumentType;
  file_name: string;
  storage_path: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_checksum: string;
  verification_status: DocumentVerificationStatus;
  ocr_raw_text?: string | null;
  extracted_metadata?: Record<string, unknown> | null;
  deficiency_notes?: string | null;
  issue_date?: string | null;
  expiry_date?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  total: number;
  documents: DocumentRecord[];
}

export interface DocumentUploadResponse {
  id: string;
  business_id: string;
  requirement_id?: string | null;
  document_type: DocumentType;
  file_name: string;
  storage_path: string;
  mime_type: string;
  file_size_bytes: number;
  sha256_checksum: string;
  verification_status: DocumentVerificationStatus;
  created_at: string;
}

/** Human-readable label for each document type */
export const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  PAN_CARD: "PAN Card",
  GST_CERTIFICATE: "GST Registration Certificate",
  UDYAM_REGISTRATION: "Udyam Registration Certificate",
  LAND_DEED_OR_LEASE: "Land Deed / Lease Agreement",
  SITE_PLAN_LAYOUT: "Site Plan / Factory Layout",
  PROJECT_REPORT_DPR: "Detailed Project Report (DPR)",
  ENVIRONMENTAL_MANAGEMENT_PLAN: "Environmental Management Plan (EMP)",
  WATER_BALANCE_CHART: "Water Balance Chart",
  POWER_SANCTION_LETTER: "Power Sanction Letter",
  FIRE_SAFETY_PLAN: "Fire Safety Plan",
  FACTORY_BUILDING_PLAN: "Factory Building Plan",
  CERTIFICATE_OF_INCORPORATION: "Certificate of Incorporation",
  OTHER: "Other Document",
};

/** Accepted MIME types matching the backend allowlist */
export const ACCEPTED_MIME_TYPES =
  ".pdf,.jpg,.jpeg,.png,.tiff,.tif,.webp,.doc,.docx,.xlsx";

export const MAX_FILE_SIZE_MB = 10;

/** Upload a document file via multipart form */
export async function uploadDocument(
  businessId: string,
  file: File,
  documentType: DocumentType,
  requirementId?: string
): Promise<DocumentUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("business_id", businessId);
  form.append("document_type", documentType);
  if (requirementId) form.append("requirement_id", requirementId);

  return apiFetch<DocumentUploadResponse>("/documents/upload", {
    method: "POST",
    body: form,
  });
}

/** List all documents for a business */
export async function fetchBusinessDocuments(
  businessId: string
): Promise<DocumentListResponse> {
  return apiFetch<DocumentListResponse>(`/documents/business/${businessId}`);
}

/** Get a single document by ID */
export async function fetchDocument(documentId: string): Promise<DocumentRecord> {
  return apiFetch<DocumentRecord>(`/documents/${documentId}`);
}

/** Delete a document */
export async function deleteDocument(documentId: string): Promise<void> {
  return apiFetch<void>(`/documents/${documentId}`, { method: "DELETE" });
}

/** Format bytes to human-readable string */
export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Verification status badge config */
export const VERIFICATION_STATUS_CONFIG: Record<
  DocumentVerificationStatus,
  { label: string; className: string }
> = {
  PENDING: {
    label: "Pending Review",
    className: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
  PROCESSING: {
    label: "Processing",
    className: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  },
  VERIFIED: {
    label: "Verified",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  },
  FLAGGED: {
    label: "Flagged",
    className: "bg-orange-500/10 text-orange-400 border-orange-500/30",
  },
  REJECTED: {
    label: "Rejected",
    className: "bg-rose-500/10 text-rose-400 border-rose-500/30",
  },
};

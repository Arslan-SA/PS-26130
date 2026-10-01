"use client";

/**
 * Document Management Page (Fragment 63 — UI).
 * Integrates DocumentUploader and shows the document health summary for the business.
 */

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useAuth } from "@/components/auth/AuthProvider";
import DocumentUploader from "@/components/documents/DocumentUploader";
import {
  DocumentRecord,
  DocumentUploadResponse,
  DOCUMENT_TYPE_LABELS,
  VERIFICATION_STATUS_CONFIG,
  fetchBusinessDocuments,
  deleteDocument,
  formatBytes,
} from "@/lib/documents";
import { fetchUserBusinesses } from "@/lib/business";

export default function DocumentsPage() {
  const { user } = useAuth();
  const [businessId, setBusinessId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUploader, setShowUploader] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const businesses = await fetchUserBusinesses();
      if (businesses?.length) {
        const biz = businesses[0];
        setBusinessId(biz.id);
        const res = await fetchBusinessDocuments(biz.id);
        setDocuments(res.documents);
      }
    } catch (err) {
      console.error("Failed to load documents", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleUploadComplete = (doc: DocumentUploadResponse) => {
    // Refresh the list after upload
    if (businessId) {
      fetchBusinessDocuments(businessId)
        .then((res) => setDocuments(res.documents))
        .catch(console.error);
    }
  };

  const handleDelete = async (id: string) => {
    setDeleteId(id);
    try {
      await deleteDocument(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
    } catch (err) {
      console.error("Delete failed", err);
    } finally {
      setDeleteId(null);
    }
  };

  // Document health stats
  const stats = {
    total: documents.length,
    verified: documents.filter((d) => d.verification_status === "VERIFIED").length,
    pending: documents.filter((d) => d.verification_status === "PENDING").length,
    flagged: documents.filter(
      (d) => d.verification_status === "FLAGGED" || d.verification_status === "REJECTED"
    ).length,
  };

  return (
    <ProtectedRoute allowedRoles={["INDUSTRY_USER", "ADMIN"]}>
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto space-y-8">

          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Link href="/dashboard" className="text-xs text-slate-500 hover:text-slate-300 transition-colors">
                  Dashboard
                </Link>
                <span className="text-slate-600">›</span>
                <span className="text-xs text-slate-300">Document Vault</span>
              </div>
              <h1 className="text-2xl font-bold text-slate-100">📂 Document Vault</h1>
              <p className="text-sm text-slate-400 mt-1">
                Upload and manage statutory regulatory documents for your enterprise
              </p>
            </div>
            <button
              onClick={() => setShowUploader((p) => !p)}
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-blue-500/20"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              {showUploader ? "Hide Uploader" : "Upload Document"}
            </button>
          </div>

          {/* Stats Bar */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "Total Documents", value: stats.total, color: "text-slate-300", bg: "bg-slate-800/60" },
              { label: "Verified", value: stats.verified, color: "text-emerald-400", bg: "bg-emerald-500/5 border-emerald-500/20" },
              { label: "Pending Review", value: stats.pending, color: "text-amber-400", bg: "bg-amber-500/5 border-amber-500/20" },
              { label: "Flagged / Rejected", value: stats.flagged, color: "text-rose-400", bg: "bg-rose-500/5 border-rose-500/20" },
            ].map((s) => (
              <div key={s.label} className={`p-4 rounded-xl border ${s.bg} border-slate-700/50`}>
                <p className={`text-2xl font-bold ${s.color}`}>{s.value}</p>
                <p className="text-xs text-slate-500 mt-0.5">{s.label}</p>
              </div>
            ))}
          </div>

          {/* Upload Panel */}
          {showUploader && businessId && (
            <div className="p-6 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md">
              <h2 className="text-base font-semibold text-slate-200 mb-4">
                Upload New Document
              </h2>
              <DocumentUploader
                businessId={businessId}
                onUploadComplete={handleUploadComplete}
              />
            </div>
          )}

          {/* Document Table */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl backdrop-blur-md overflow-hidden">
            <div className="p-5 border-b border-slate-800">
              <h2 className="text-base font-semibold text-slate-200">
                Uploaded Documents
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                All statutory documents uploaded for your enterprise
              </p>
            </div>

            {loading ? (
              <div className="p-12 flex justify-center">
                <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
              </div>
            ) : documents.length === 0 ? (
              <div className="p-12 text-center">
                <div className="w-14 h-14 mx-auto rounded-full bg-slate-800 flex items-center justify-center mb-3">
                  <svg className="w-7 h-7 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                  </svg>
                </div>
                <p className="text-slate-400 text-sm font-medium">No documents uploaded yet</p>
                <p className="text-slate-600 text-xs mt-1">
                  Click "Upload Document" to add your first regulatory document
                </p>
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60">
                {documents.map((doc) => {
                  const statusCfg = VERIFICATION_STATUS_CONFIG[doc.verification_status];
                  return (
                    <div
                      key={doc.id}
                      className="flex items-center gap-4 px-5 py-4 hover:bg-slate-800/40 transition-colors group"
                    >
                      {/* File icon */}
                      <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-slate-700/60 flex items-center justify-center">
                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                            d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                        </svg>
                      </div>

                      {/* Main info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-slate-200 truncate">
                          {doc.file_name}
                        </p>
                        <div className="flex items-center gap-3 mt-0.5">
                          <span className="text-xs text-slate-500">
                            {DOCUMENT_TYPE_LABELS[doc.document_type]}
                          </span>
                          <span className="text-slate-700">·</span>
                          <span className="text-xs text-slate-500">
                            {formatBytes(doc.file_size_bytes)}
                          </span>
                          <span className="text-slate-700">·</span>
                          <span className="text-xs font-mono text-slate-600">
                            {doc.sha256_checksum.slice(0, 10)}…
                          </span>
                        </div>
                      </div>

                      {/* Status badge */}
                      <span
                        className={`flex-shrink-0 text-[11px] font-semibold px-2.5 py-1 rounded-full border ${statusCfg.className}`}
                      >
                        {statusCfg.label}
                      </span>

                      {/* Expiry warning */}
                      {doc.expiry_date && (
                        <span className="flex-shrink-0 text-[11px] text-amber-400 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded">
                          Expires {doc.expiry_date}
                        </span>
                      )}

                      {/* Delete */}
                      {user?.role === "INDUSTRY_USER" && (
                        <button
                          onClick={() => handleDelete(doc.id)}
                          disabled={deleteId === doc.id}
                          className="opacity-0 group-hover:opacity-100 flex-shrink-0 text-slate-500 hover:text-rose-400 transition-all"
                          aria-label="Delete document"
                        >
                          {deleteId === doc.id ? (
                            <div className="w-4 h-4 border-2 border-rose-400 border-t-transparent rounded-full animate-spin" />
                          ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                                d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                            </svg>
                          )}
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Tip Banner */}
          <div className="p-4 bg-blue-500/5 border border-blue-500/20 rounded-xl">
            <p className="text-xs text-blue-300">
              <span className="font-semibold">ℹ️ Document Intelligence:</span>{" "}
              All uploaded documents are automatically processed for OCR text extraction,
              entity recognition, and statutory compliance matching. Verification status
              will update within minutes of upload.
            </p>
          </div>
        </div>
      </div>
    </ProtectedRoute>
  );
}

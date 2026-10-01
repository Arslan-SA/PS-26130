"use client";

/**
 * DocumentUploader — Drag-and-drop file upload component (Fragment 63).
 *
 * Features:
 * - Drag-and-drop zone with hover/active visual feedback
 * - Click-to-browse file picker with MIME/extension filtering
 * - Client-side file size validation (≤10 MB)
 * - Document type selector (statutory categories)
 * - Upload progress indicator
 * - Success/error state display
 * - Uploaded file preview list with size and checksum
 */

import React, { useCallback, useRef, useState } from "react";
import {
  ACCEPTED_MIME_TYPES,
  DOCUMENT_TYPE_LABELS,
  DocumentType,
  DocumentUploadResponse,
  MAX_FILE_SIZE_MB,
  formatBytes,
  uploadDocument,
} from "@/lib/documents";

interface UploadedFile {
  file: File;
  result?: DocumentUploadResponse;
  error?: string;
  status: "pending" | "uploading" | "done" | "error";
}

interface DocumentUploaderProps {
  businessId: string;
  requirementId?: string;
  onUploadComplete?: (doc: DocumentUploadResponse) => void;
}

const DOC_TYPES = Object.entries(DOCUMENT_TYPE_LABELS) as [
  DocumentType,
  string
][];

export default function DocumentUploader({
  businessId,
  requirementId,
  onUploadComplete,
}: DocumentUploaderProps) {
  const [selectedType, setSelectedType] = useState<DocumentType>("OTHER");
  const [dragOver, setDragOver] = useState(false);
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  // -------------------------------------------------------------------------
  // Validation
  // -------------------------------------------------------------------------
  const validateFile = (file: File): string | null => {
    const sizeMb = file.size / (1024 * 1024);
    if (sizeMb > MAX_FILE_SIZE_MB)
      return `File is ${sizeMb.toFixed(1)} MB — maximum allowed is ${MAX_FILE_SIZE_MB} MB.`;
    const ext = "." + file.name.split(".").pop()?.toLowerCase();
    const allowed = ACCEPTED_MIME_TYPES.split(",");
    if (!allowed.includes(ext))
      return `File type "${ext}" is not accepted. Upload PDF, JPEG, PNG, TIFF, DOCX, or XLSX.`;
    return null;
  };

  // -------------------------------------------------------------------------
  // Upload handler
  // -------------------------------------------------------------------------
  const processFiles = useCallback(
    async (rawFiles: FileList | File[]) => {
      const fileArray = Array.from(rawFiles);
      const newEntries: UploadedFile[] = fileArray.map((f) => {
        const err = validateFile(f);
        return { file: f, status: err ? "error" : "pending", error: err ?? undefined };
      });

      setFiles((prev) => [...prev, ...newEntries]);

      for (let i = 0; i < newEntries.length; i++) {
        if (newEntries[i].status === "error") continue;

        const idx = files.length + i;
        setFiles((prev) =>
          prev.map((f, j) => (j === idx ? { ...f, status: "uploading" } : f))
        );

        try {
          const result = await uploadDocument(
            businessId,
            newEntries[i].file,
            selectedType,
            requirementId
          );
          setFiles((prev) =>
            prev.map((f, j) =>
              j === idx ? { ...f, status: "done", result } : f
            )
          );
          onUploadComplete?.(result);
        } catch (err: unknown) {
          const msg =
            err instanceof Error ? err.message : "Upload failed. Please try again.";
          setFiles((prev) =>
            prev.map((f, j) =>
              j === idx ? { ...f, status: "error", error: msg } : f
            )
          );
        }
      }
    },
    [businessId, selectedType, requirementId, files.length, onUploadComplete]
  );

  // -------------------------------------------------------------------------
  // Drag events
  // -------------------------------------------------------------------------
  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };
  const onDragLeave = () => setDragOver(false);
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer.files.length) processFiles(e.dataTransfer.files);
  };
  const onInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.length) processFiles(e.target.files);
  };

  const removeFile = (idx: number) =>
    setFiles((prev) => prev.filter((_, i) => i !== idx));

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className="space-y-4">
      {/* Document Type Selector */}
      <div>
        <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
          Document Category
        </label>
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value as DocumentType)}
          className="w-full bg-slate-800/80 border border-slate-700 text-slate-100 rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 transition-colors"
        >
          {DOC_TYPES.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`
          relative flex flex-col items-center justify-center gap-3
          border-2 border-dashed rounded-xl p-8 cursor-pointer
          transition-all duration-200 select-none
          ${
            dragOver
              ? "border-blue-400 bg-blue-500/10 scale-[1.01]"
              : "border-slate-600 bg-slate-800/40 hover:border-slate-500 hover:bg-slate-800/60"
          }
        `}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_MIME_TYPES}
          onChange={onInputChange}
          className="hidden"
          aria-label="Upload regulatory document"
        />

        {/* Upload Icon */}
        <div
          className={`w-14 h-14 rounded-full flex items-center justify-center transition-colors
            ${dragOver ? "bg-blue-500/20" : "bg-slate-700/60"}`}
        >
          <svg
            className={`w-7 h-7 transition-colors ${dragOver ? "text-blue-400" : "text-slate-400"}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"
            />
          </svg>
        </div>

        <div className="text-center">
          <p className="text-sm font-medium text-slate-200">
            {dragOver ? "Drop files here" : "Drag & drop files here"}
          </p>
          <p className="text-xs text-slate-500 mt-0.5">
            or{" "}
            <span className="text-blue-400 hover:text-blue-300 underline underline-offset-2">
              click to browse
            </span>
          </p>
        </div>

        <div className="flex flex-wrap justify-center gap-1 mt-1">
          {["PDF", "JPEG", "PNG", "TIFF", "DOCX", "XLSX"].map((ext) => (
            <span
              key={ext}
              className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-400 border border-slate-600/50"
            >
              {ext}
            </span>
          ))}
        </div>
        <p className="text-[11px] text-slate-500">Max {MAX_FILE_SIZE_MB} MB per file</p>
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Uploads ({files.length})
          </p>
          {files.map((f, idx) => (
            <div
              key={idx}
              className={`flex items-start gap-3 p-3 rounded-lg border transition-all
                ${
                  f.status === "done"
                    ? "bg-emerald-500/5 border-emerald-500/20"
                    : f.status === "error"
                    ? "bg-rose-500/5 border-rose-500/20"
                    : f.status === "uploading"
                    ? "bg-blue-500/5 border-blue-500/20"
                    : "bg-slate-800/50 border-slate-700/50"
                }
              `}
            >
              {/* File Icon */}
              <div className="flex-shrink-0 w-8 h-8 rounded bg-slate-700/60 flex items-center justify-center mt-0.5">
                <svg
                  className="w-4 h-4 text-slate-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={1.5}
                    d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z"
                  />
                </svg>
              </div>

              {/* File Info */}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-200 truncate">
                  {f.file.name}
                </p>
                <p className="text-xs text-slate-500">{formatBytes(f.file.size)}</p>

                {/* Status */}
                {f.status === "uploading" && (
                  <div className="mt-1.5 flex items-center gap-1.5">
                    <div className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
                    <span className="text-xs text-blue-400">Uploading…</span>
                  </div>
                )}
                {f.status === "done" && f.result && (
                  <div className="mt-1 space-y-0.5">
                    <p className="text-[11px] text-emerald-400 font-medium">
                      ✓ Uploaded successfully
                    </p>
                    <p className="text-[10px] font-mono text-slate-500 truncate">
                      SHA-256: {f.result.sha256_checksum.slice(0, 24)}…
                    </p>
                  </div>
                )}
                {f.status === "error" && (
                  <p className="mt-1 text-xs text-rose-400">{f.error}</p>
                )}
              </div>

              {/* Remove Button */}
              {f.status !== "uploading" && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(idx);
                  }}
                  className="flex-shrink-0 text-slate-500 hover:text-rose-400 transition-colors"
                  aria-label="Remove file"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

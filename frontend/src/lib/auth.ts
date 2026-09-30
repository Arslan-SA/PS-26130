/**
 * Frontend Authentication, Token Management & API Client Utilities.
 */

export type UserRole = "INDUSTRY_USER" | "DEPARTMENT_OFFICER" | "INSPECTOR" | "ADMIN";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  phone?: string | null;
  department_id?: string | null;
  designation?: string | null;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("udyamsetu_access_token");
}

export function setStoredTokens(tokens: { access_token: string; refresh_token: string }) {
  if (typeof window === "undefined") return;
  localStorage.setItem("udyamsetu_access_token", tokens.access_token);
  localStorage.setItem("udyamsetu_refresh_token", tokens.refresh_token);
}

export function clearStoredTokens() {
  if (typeof window === "undefined") return;
  localStorage.removeItem("udyamsetu_access_token");
  localStorage.removeItem("udyamsetu_refresh_token");
  localStorage.removeItem("udyamsetu_user");
}

export async function apiFetch<T = any>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getStoredToken();
  const headers = new Headers(options.headers || {});
  
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const url = endpoint.startsWith("http") ? endpoint : `${API_BASE}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;
  const response = await fetch(url, { ...options, headers });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData?.error?.message || `Request failed with status ${response.status}`);
  }

  return response.json();
}

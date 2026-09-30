"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/components/auth/AuthProvider";
import { apiFetch, UserRole } from "@/lib/auth";

interface DemoAccount {
  label: string;
  role: UserRole;
  email: string;
  badgeColor: string;
}

const DEMO_ACCOUNTS: DemoAccount[] = [
  { label: "Industry User", role: "INDUSTRY_USER", email: "rajesh.patel@bharatsteel.com", badgeColor: "bg-blue-100 text-blue-800 border-blue-200" },
  { label: "Dept Officer", role: "DEPARTMENT_OFFICER", email: "officer.verma@spcb.gov.in", badgeColor: "bg-emerald-100 text-emerald-800 border-emerald-200" },
  { label: "Inspector", role: "INSPECTOR", email: "inspector.sharma@fire.gov.in", badgeColor: "bg-amber-100 text-amber-800 border-amber-200" },
  { label: "Admin", role: "ADMIN", email: "admin.super@udyamsetu.gov.in", badgeColor: "bg-purple-100 text-purple-800 border-purple-200" },
];

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleQuickFill = (acc: DemoAccount) => {
    setEmail(acc.email);
    setPassword("Enterprise@2026");
    setErrorMsg(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setIsSubmitting(true);

    try {
      const data = await apiFetch<{
        tokens: {
          access_token: string;
          refresh_token: string;
          token_type: string;
          expires_in: number;
        };
        user: {
          id: string;
          email: string;
          full_name: string;
          role: UserRole;
          is_verified: boolean;
          is_active: boolean;
          created_at: string;
        };
      }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      login(data.tokens, data.user);

      // Route by role
      switch (data.user.role) {
        case "INDUSTRY_USER":
          router.push("/dashboard");
          break;
        case "DEPARTMENT_OFFICER":
          router.push("/officer/inbox");
          break;
        case "INSPECTOR":
          router.push("/inspector/schedule");
          break;
        case "ADMIN":
          router.push("/admin");
          break;
        default:
          router.push("/dashboard");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Invalid email or password. Please verify credentials.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-md border border-slate-200">
        <div>
          <div className="h-12 w-12 bg-gov-blue text-white rounded-lg flex items-center justify-center font-bold text-xl mx-auto shadow-sm">
            US
          </div>
          <h2 className="mt-4 text-center text-2xl font-extrabold text-slate-900 tracking-tight">
            Sign in to UdyamSetu AI
          </h2>
          <p className="mt-2 text-center text-sm text-slate-600">
            Intelligent Single-Window Regulatory & Compliance Portal
          </p>
        </div>

        {/* Quick Demo Credentials Banner */}
        <div className="bg-slate-50 p-3.5 rounded-lg border border-slate-200">
          <p className="text-xs font-semibold text-slate-600 mb-2 uppercase tracking-wider">
            Quick Fill Demo Accounts (SIH Evaluator Mode):
          </p>
          <div className="grid grid-cols-2 gap-2">
            {DEMO_ACCOUNTS.map((acc) => (
              <button
                key={acc.role}
                type="button"
                onClick={() => handleQuickFill(acc)}
                className={`text-xs px-2.5 py-1.5 rounded border font-medium transition-all text-left truncate ${acc.badgeColor} hover:opacity-90`}
              >
                {acc.label}
              </button>
            ))}
          </div>
        </div>

        {errorMsg && (
          <div className="bg-red-50 border-l-4 border-red-500 p-3.5 rounded">
            <p className="text-sm text-red-700">{errorMsg}</p>
          </div>
        )}

        <form className="mt-6 space-y-5" onSubmit={handleSubmit}>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Work / Government Email
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. user@enterprise.com"
              className="appearance-none block w-full px-3.5 py-2.5 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-gov-sky focus:border-transparent text-sm"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-1">
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider">
                Password
              </label>
            </div>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              className="appearance-none block w-full px-3.5 py-2.5 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-gov-sky focus:border-transparent text-sm"
            />
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gov-blue hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gov-blue transition-colors disabled:opacity-60"
            >
              {isSubmitting ? (
                <span className="flex items-center space-x-2">
                  <span className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Authenticating...</span>
                </span>
              ) : (
                "Sign In"
              )}
            </button>
          </div>
        </form>

        <div className="text-center pt-2">
          <p className="text-xs text-slate-600">
            Don&apos;t have an industrial enterprise account?{" "}
            <Link href="/register" className="font-semibold text-gov-sky hover:underline">
              Register Enterprise
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

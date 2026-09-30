"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { apiFetch, UserRole } from "@/lib/auth";

export default function RegisterPage() {
  const router = useRouter();

  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    phone: "",
    role: "INDUSTRY_USER" as UserRole,
    departmentId: "",
    designation: "",
    password: "",
    confirmPassword: "",
  });

  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const validatePassword = (pwd: string) => {
    if (pwd.length < 8) return "Password must be at least 8 characters long";
    if (!/[A-Z]/.test(pwd)) return "Password must contain at least one uppercase letter";
    if (!/[a-z]/.test(pwd)) return "Password must contain at least one lowercase letter";
    if (!/[0-9]/.test(pwd)) return "Password must contain at least one number";
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(pwd)) return "Password must contain at least one special character";
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSuccessMsg(null);

    const pwdError = validatePassword(formData.password);
    if (pwdError) {
      setErrorMsg(pwdError);
      return;
    }

    if (formData.password !== formData.confirmPassword) {
      setErrorMsg("Passwords do not match");
      return;
    }

    setIsSubmitting(true);

    try {
      await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({
          full_name: formData.fullName,
          email: formData.email,
          phone: formData.phone || null,
          role: formData.role,
          department_id: formData.departmentId || null,
          designation: formData.designation || null,
          password: formData.password,
        }),
      });

      setSuccessMsg("Registration successful! Redirecting to login...");
      setTimeout(() => {
        router.push("/login");
      }, 1500);
    } catch (err: any) {
      setErrorMsg(err.message || "Registration failed. Please check the details.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-[85vh] flex items-center justify-center bg-slate-50 py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-lg w-full space-y-8 bg-white p-8 rounded-xl shadow-md border border-slate-200">
        <div>
          <div className="h-12 w-12 bg-gov-blue text-white rounded-lg flex items-center justify-center font-bold text-xl mx-auto shadow-sm">
            US
          </div>
          <h2 className="mt-4 text-center text-2xl font-extrabold text-slate-900 tracking-tight">
            Register Industrial Account
          </h2>
          <p className="mt-2 text-center text-sm text-slate-600">
            Join India&apos;s Next-Gen Industrial Clearance & Compliance Ecosystem
          </p>
        </div>

        {errorMsg && (
          <div className="bg-red-50 border-l-4 border-red-500 p-3.5 rounded">
            <p className="text-sm text-red-700">{errorMsg}</p>
          </div>
        )}

        {successMsg && (
          <div className="bg-emerald-50 border-l-4 border-emerald-500 p-3.5 rounded">
            <p className="text-sm text-emerald-700 font-medium">{successMsg}</p>
          </div>
        )}

        <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Authorized Representative Name
            </label>
            <input
              type="text"
              name="fullName"
              required
              value={formData.fullName}
              onChange={handleChange}
              placeholder="e.g. Rajesh Patel"
              className="appearance-none block w-full px-3.5 py-2.5 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-gov-sky focus:border-transparent text-sm"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Corporate Email
              </label>
              <input
                type="email"
                name="email"
                required
                value={formData.email}
                onChange={handleChange}
                placeholder="rajesh@bharatsteel.com"
                className="appearance-none block w-full px-3.5 py-2.5 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-gov-sky focus:border-transparent text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Mobile Number
              </label>
              <input
                type="tel"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                placeholder="+91 9876543210"
                className="appearance-none block w-full px-3.5 py-2.5 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-gov-sky focus:border-transparent text-sm"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
              Role Classification
            </label>
            <select
              name="role"
              value={formData.role}
              onChange={handleChange}
              className="block w-full px-3.5 py-2.5 border border-slate-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-gov-sky focus:border-transparent text-sm bg-white"
            >
              <option value="INDUSTRY_USER">Industry / MSME Enterprise Representative</option>
              <option value="DEPARTMENT_OFFICER">Statutory Department Clearance Officer</option>
              <option value="INSPECTOR">Field Verification Inspector</option>
              <option value="ADMIN">System Administrator</option>
            </select>
          </div>

          {formData.role !== "INDUSTRY_USER" && (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 bg-slate-50 p-3 rounded border border-slate-200">
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Department ID / Dept Code
                </label>
                <input
                  type="text"
                  name="departmentId"
                  value={formData.departmentId}
                  onChange={handleChange}
                  placeholder="e.g. SPCB-MH-01"
                  className="appearance-none block w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                  Official Designation
                </label>
                <input
                  type="text"
                  name="designation"
                  value={formData.designation}
                  onChange={handleChange}
                  placeholder="e.g. Assistant Environmental Engineer"
                  className="appearance-none block w-full px-3 py-2 border border-slate-300 rounded-md text-sm"
                />
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Password
              </label>
              <input
                type="password"
                name="password"
                required
                value={formData.password}
                onChange={handleChange}
                placeholder="••••••••••••"
                className="appearance-none block w-full px-3.5 py-2.5 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-gov-sky focus:border-transparent text-sm"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1">
                Confirm Password
              </label>
              <input
                type="password"
                name="confirmPassword"
                required
                value={formData.confirmPassword}
                onChange={handleChange}
                placeholder="••••••••••••"
                className="appearance-none block w-full px-3.5 py-2.5 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-gov-sky focus:border-transparent text-sm"
              />
            </div>
          </div>

          <div className="text-xs text-slate-500 space-y-1 bg-slate-50 p-2.5 rounded border border-slate-200">
            <span className="font-semibold text-slate-700">Security Requirement:</span> Minimum 8 characters with at least 1 uppercase letter, 1 lowercase letter, 1 number, and 1 special symbol.
          </div>

          <div className="pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gov-blue hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gov-blue transition-colors disabled:opacity-60"
            >
              {isSubmitting ? (
                <span className="flex items-center space-x-2">
                  <span className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></span>
                  <span>Creating Account...</span>
                </span>
              ) : (
                "Complete Registration"
              )}
            </button>
          </div>
        </form>

        <div className="text-center pt-2">
          <p className="text-xs text-slate-600">
            Already have an active account?{" "}
            <Link href="/login" className="font-semibold text-gov-sky hover:underline">
              Sign In
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

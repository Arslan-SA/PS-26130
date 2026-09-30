"use client";

import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { OnboardingWizard } from "@/components/onboarding/OnboardingWizard";

export default function OnboardingPage() {
  return (
    <ProtectedRoute allowedRoles={["INDUSTRY_USER", "ADMIN"]}>
      <div className="min-h-screen bg-slate-950 text-slate-100 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto mb-8">
          <div className="flex items-center gap-2 text-sm text-blue-400 mb-2 font-mono">
            <span>UdyamSetu National Single-Window Registry</span>
            <span>/</span>
            <span>Onboarding</span>
          </div>
        </div>
        <OnboardingWizard />
      </div>
    </ProtectedRoute>
  );
}

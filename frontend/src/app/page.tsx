import React from "react";
import { 
  Building2, 
  ShieldCheck, 
  FileText, 
  Cpu, 
  GitFork, 
  Sparkles, 
  TrendingUp, 
  CheckCircle2, 
  ArrowRight,
  ClipboardList,
  AlertCircle
} from "lucide-react";

export default function HomePage() {
  return (
    <div className="space-y-16 py-10 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto">
      {/* Hero Section */}
      <section className="bg-white border border-slate-200 rounded-xl p-8 sm:p-12 shadow-sm text-center md:text-left md:flex items-center justify-between gap-10">
        <div className="max-w-2xl space-y-5">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-200 text-gov-blue text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5 text-blue-600" />
            AI-Powered Industrial Facilitation & Compliance Platform
          </div>
          <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight leading-tight">
            From <span className="text-gov-blue">"Which approvals do I need?"</span> to <span className="text-emerald-700">"Here is exactly what to do next."</span>
          </h1>
          <p className="text-base sm:text-lg text-slate-600 leading-relaxed">
            Navigating statutory licenses, Consent to Establish (CTE), Fire NOCs, Factory Licenses, compliance deadlines, and industrial subsidies with deterministic regulatory precision and intelligent assistance.
          </p>
          <div className="flex flex-wrap gap-4 pt-2">
            <a
              href="/register"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-gov-blue text-white font-medium hover:bg-slate-800 shadow transition-all"
            >
              Get Started as Industry / MSME
              <ArrowRight className="w-4 h-4" />
            </a>
            <a
              href="/login"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-slate-100 text-slate-800 font-medium hover:bg-slate-200 border border-slate-300 transition-all"
            >
              Department Officer Sign-in
            </a>
          </div>
        </div>

        <div className="mt-8 md:mt-0 grid grid-cols-2 gap-4 w-full md:w-80">
          <div className="bg-slate-50 border border-slate-200 p-4 rounded-lg text-center">
            <div className="text-2xl font-bold text-gov-blue">100%</div>
            <div className="text-xs text-slate-600 font-medium mt-1">Rule-Driven Accuracy</div>
          </div>
          <div className="bg-slate-50 border border-slate-200 p-4 rounded-lg text-center">
            <div className="text-2xl font-bold text-emerald-700">DAG</div>
            <div className="text-xs text-slate-600 font-medium mt-1">Dependency Graphs</div>
          </div>
          <div className="bg-slate-50 border border-slate-200 p-4 rounded-lg text-center">
            <div className="text-2xl font-bold text-blue-700">OCR</div>
            <div className="text-xs text-slate-600 font-medium mt-1">Document Scrutiny</div>
          </div>
          <div className="bg-slate-50 border border-slate-200 p-4 rounded-lg text-center">
            <div className="text-2xl font-bold text-amber-700">SLA</div>
            <div className="text-xs text-slate-600 font-medium mt-1">Pendency Monitoring</div>
          </div>
        </div>
      </section>

      {/* Core Differentiators */}
      <section id="features" className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">
            Intelligent Differentiators
          </h2>
          <p className="text-sm text-slate-600">
            Not another generic CRUD portal — an active intelligence and orchestration layer above forms.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white border border-slate-200 p-6 rounded-xl space-y-3 shadow-sm hover:border-slate-300 transition-colors">
            <div className="w-10 h-10 rounded-lg bg-blue-50 text-gov-blue flex items-center justify-center font-bold">
              <Cpu className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">AI Approval Navigator</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Analyzes sector, scale, capital investment, and location to calculate required statutory approvals using deterministic regulatory matrices.
            </p>
          </div>

          <div className="bg-white border border-slate-200 p-6 rounded-xl space-y-3 shadow-sm hover:border-slate-300 transition-colors">
            <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-700 flex items-center justify-center font-bold">
              <GitFork className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Approval Dependency Graph</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Visualizes prerequisite dependencies (e.g. Land → Consent to Establish → Power Sanction → Consent to Operate) with critical path guidance.
            </p>
          </div>

          <div className="bg-white border border-slate-200 p-6 rounded-xl space-y-3 shadow-sm hover:border-slate-300 transition-colors">
            <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
              <FileText className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Document Intelligence & OCR</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Extracts fields, detects expired licenses, verifies PAN/GSTIN consistency against business profiles, and catches missing attachments before submission.
            </p>
          </div>

          <div className="bg-white border border-slate-200 p-6 rounded-xl space-y-3 shadow-sm hover:border-slate-300 transition-colors">
            <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-700 flex items-center justify-center font-bold">
              <ClipboardList className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">AI Next-Action Engine</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Dynamically turns complex departmental deficiency notes and approval stages into simple, structured action items for business users.
            </p>
          </div>

          <div className="bg-white border border-slate-200 p-6 rounded-xl space-y-3 shadow-sm hover:border-slate-300 transition-colors">
            <div className="w-10 h-10 rounded-lg bg-teal-50 text-teal-700 flex items-center justify-center font-bold">
              <TrendingUp className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Government Scheme Matching</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Automated matching against central and state industrial subsidy schemes (e.g., Capital Investment Subsidy, Green Technology Rebate) with clear criteria.
            </p>
          </div>

          <div className="bg-white border border-slate-200 p-6 rounded-xl space-y-3 shadow-sm hover:border-slate-300 transition-colors">
            <div className="w-10 h-10 rounded-lg bg-purple-50 text-purple-700 flex items-center justify-center font-bold">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-lg font-bold text-slate-900">Compliance Calendar & Alerts</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Continuous tracking of recurring statutory returns, environmental renewals, fire safety audits, and factory inspections with SLA risk indicators.
            </p>
          </div>
        </div>
      </section>

      {/* Role-Based Portals */}
      <section id="roles" className="space-y-6">
        <div className="text-center max-w-2xl mx-auto space-y-2">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">
            Multi-Role Governance & Collaboration
          </h2>
          <p className="text-sm text-slate-600">
            Dedicated portals with Role-Based Access Control (RBAC) ensuring data isolation and operational clarity.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
          <div className="border border-slate-200 bg-white rounded-xl p-5 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-blue-600">Role 01</div>
            <h4 className="text-base font-bold text-slate-900">Industry / MSME</h4>
            <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
              <li>Business Profile setup</li>
              <li>Approval discovery & roadmap</li>
              <li>Document OCR & pre-validation</li>
              <li>Applications & query replies</li>
              <li>Compliance & Scheme discovery</li>
            </ul>
          </div>

          <div className="border border-slate-200 bg-white rounded-xl p-5 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-emerald-600">Role 02</div>
            <h4 className="text-base font-bold text-slate-900">Department Officer</h4>
            <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
              <li>Department-scoped inbox</li>
              <li>Document verification review</li>
              <li>Structured deficiency notes</li>
              <li>Inspection assignment</li>
              <li>Statutory grant / rejection</li>
            </ul>
          </div>

          <div className="border border-slate-200 bg-white rounded-xl p-5 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-amber-600">Role 03</div>
            <h4 className="text-base font-bold text-slate-900">Field Inspector</h4>
            <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
              <li>Assigned site visit queues</li>
              <li>Statutory inspection checklists</li>
              <li>Geolocated report submission</li>
              <li>Photo/evidence upload</li>
            </ul>
          </div>

          <div className="border border-slate-200 bg-white rounded-xl p-5 space-y-3">
            <div className="text-xs font-bold uppercase tracking-wider text-purple-600">Role 04</div>
            <h4 className="text-base font-bold text-slate-900">System Admin</h4>
            <ul className="text-xs text-slate-600 space-y-1.5 list-disc pl-4">
              <li>Master approval catalog</li>
              <li>Rule engine & scheme management</li>
              <li>Cross-department SLA analytics</li>
              <li>Immutable audit logs</li>
            </ul>
          </div>
        </div>
      </section>
    </div>
  );
}

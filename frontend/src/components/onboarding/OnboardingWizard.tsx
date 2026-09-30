"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import {
  EntityType,
  MSMECategory,
  IndustryScale,
  PollutionCategory,
  OnboardingPayload,
  submitOnboarding,
} from "@/lib/business";

export function OnboardingWizard() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successData, setSuccessData] = useState<any | null>(null);

  // Form State
  const [formData, setFormData] = useState({
    // Step 1: Legal Entity
    legal_name: "",
    trade_name: "",
    entity_type: "PRIVATE_LIMITED" as EntityType,
    pan: "",
    gstin: "",
    udyam_number: "",
    cin: "",
    msme_category: "SMALL" as MSMECategory,
    incorporation_date: "",
    website: "",

    // Step 2: Manufacturing & Activity
    nic_code: "",
    manufacturing_activity: "",
    products_services: "",
    industry_scale: "SMALL_SCALE" as IndustryScale,
    pollution_category: "GREEN" as PollutionCategory,

    // Step 3: Location
    state: "Maharashtra",
    district: "Pune",
    city: "Pune",
    pincode: "",
    full_address: "",
    plot_number: "",
    industrial_area: "Chakan Industrial Park",
    latitude: 18.76,
    longitude: 73.85,

    // Step 4: Workforce & Investment
    total_employees: 35,
    plant_machinery_investment: 15000000,
    land_area_sqm: 4500,
    annual_turnover: 50000000,
    power_requirement_kw: 150,
    water_requirement_kld: 15,

    // Step 5: Contact
    contact_person: "",
    contact_phone: "",
    contact_email: "",
  });

  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>
  ) => {
    const { name, value, type } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: type === "number" ? (value === "" ? 0 : Number(value)) : value,
    }));
  };

  const validateStep = (step: number): boolean => {
    setError(null);
    if (step === 1) {
      if (!formData.legal_name.trim()) {
        setError("Legal Enterprise Name is required.");
        return false;
      }
      if (!formData.pan.trim() || formData.pan.trim().length !== 10) {
        setError("A valid 10-character PAN is required.");
        return false;
      }
    }
    if (step === 2) {
      if (!formData.manufacturing_activity.trim()) {
        setError("Manufacturing / industrial activity description is required.");
        return false;
      }
    }
    if (step === 3) {
      if (!formData.state.trim() || !formData.district.trim()) {
        setError("State and District are required.");
        return false;
      }
      if (!formData.pincode.trim() || formData.pincode.trim().length !== 6) {
        setError("A valid 6-digit Pincode is required.");
        return false;
      }
    }
    if (step === 5) {
      if (!formData.contact_person.trim()) {
        setError("Contact representative name is required.");
        return false;
      }
    }
    return true;
  };

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep((prev) => Math.min(prev + 1, 5));
    }
  };

  const handleBack = () => {
    setError(null);
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateStep(5)) return;

    setLoading(true);
    setError(null);

    const payload: OnboardingPayload = {
      business: {
        legal_name: formData.legal_name,
        trade_name: formData.trade_name || undefined,
        entity_type: formData.entity_type,
        pan: formData.pan.toUpperCase(),
        gstin: formData.gstin ? formData.gstin.toUpperCase() : undefined,
        udyam_number: formData.udyam_number || undefined,
        cin: formData.cin ? formData.cin.toUpperCase() : undefined,
        msme_category: formData.msme_category,
        incorporation_date: formData.incorporation_date || undefined,
        website: formData.website || undefined,
      },
      profile: {
        nic_code: formData.nic_code || undefined,
        manufacturing_activity: formData.manufacturing_activity,
        products_services: formData.products_services || undefined,
        industry_scale: formData.industry_scale,
        pollution_category: formData.pollution_category,
        state: formData.state,
        district: formData.district,
        city: formData.city,
        pincode: formData.pincode,
        full_address: formData.full_address || undefined,
        plot_number: formData.plot_number || undefined,
        industrial_area: formData.industrial_area || undefined,
        latitude: formData.latitude || undefined,
        longitude: formData.longitude || undefined,
        total_employees: formData.total_employees,
        plant_machinery_investment: formData.plant_machinery_investment,
        land_area_sqm: formData.land_area_sqm,
        annual_turnover: formData.annual_turnover,
        power_requirement_kw: formData.power_requirement_kw,
        water_requirement_kld: formData.water_requirement_kld,
        contact_person: formData.contact_person,
        contact_phone: formData.contact_phone || undefined,
        contact_email: formData.contact_email || undefined,
      },
    };

    try {
      const response = await submitOnboarding(payload);
      setSuccessData(response);
    } catch (err: any) {
      setError(err.message || "Failed to onboard enterprise. Please verify details.");
    } finally {
      setLoading(false);
    }
  };

  const steps = [
    { id: 1, title: "Enterprise Identity", desc: "Legal entity & statutory IDs" },
    { id: 2, title: "Activity & CPCB", desc: "NIC & Environmental Category" },
    { id: 3, title: "Location & Plot", desc: "Industrial park & geo coordinates" },
    { id: 4, title: "Workforce & Capital", desc: "Investment, power & water load" },
    { id: 5, title: "Contact & Review", desc: "Designated nodal officer" },
  ];

  if (successData) {
    return (
      <div className="max-w-3xl mx-auto p-8 bg-slate-900/90 border border-emerald-500/40 rounded-2xl shadow-2xl backdrop-blur-xl text-center">
        <div className="w-16 h-16 bg-emerald-500/20 text-emerald-400 rounded-full flex items-center justify-center mx-auto mb-4 border border-emerald-500/30">
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Industrial Enterprise Onboarded!</h2>
        <p className="text-slate-300 text-sm mb-6">
          <span className="font-semibold text-emerald-400">{successData.business.legal_name}</span> has been registered into the UdyamSetu National Single-Window Registry.
        </p>

        <div className="bg-slate-800/80 rounded-xl p-6 text-left border border-slate-700/60 mb-6">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400 mb-3">
            Recommended Next Steps:
          </h3>
          <ul className="space-y-2">
            {successData.next_steps.map((step: string, idx: number) => (
              <li key={idx} className="flex items-start text-sm text-slate-200">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center text-xs font-bold mr-3 mt-0.5">
                  {idx + 1}
                </span>
                {step}
              </li>
            ))}
          </ul>
        </div>

        <div className="flex justify-center gap-4">
          <button
            onClick={() => router.push("/dashboard")}
            className="px-6 py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-medium rounded-xl shadow-lg transition-all"
          >
            Go to Enterprise Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto bg-slate-900/80 border border-slate-800 rounded-2xl shadow-2xl backdrop-blur-md overflow-hidden">
      {/* Wizard Progress Header */}
      <div className="bg-slate-950/60 p-6 border-b border-slate-800">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Industrial Enterprise Onboarding</h1>
            <p className="text-slate-400 text-sm mt-1">Register your unit to generate a unified statutory approval roadmap.</p>
          </div>
          <span className="text-xs font-semibold px-3 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/30 rounded-full">
            Step {currentStep} of 5
          </span>
        </div>

        {/* Step Indicator Pills */}
        <div className="grid grid-cols-5 gap-2">
          {steps.map((step) => {
            const isActive = currentStep === step.id;
            const isCompleted = currentStep > step.id;
            return (
              <div
                key={step.id}
                className={`p-2.5 rounded-lg border text-left transition-all ${
                  isActive
                    ? "bg-blue-600/20 border-blue-500 text-blue-300"
                    : isCompleted
                    ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-300"
                    : "bg-slate-900/40 border-slate-800 text-slate-500"
                }`}
              >
                <div className="flex items-center gap-1.5 text-xs font-semibold">
                  <span>0{step.id}</span>
                  {isCompleted && <span>✓</span>}
                </div>
                <div className="text-xs font-medium truncate mt-0.5">{step.title}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mx-6 mt-6 p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm flex items-center gap-3">
          <svg className="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>{error}</span>
        </div>
      )}

      {/* Form Steps */}
      <form onSubmit={handleSubmit} className="p-6 md:p-8 space-y-6">
        {/* Step 1: Legal Entity Details */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Enterprise Legal Structure & Identifiers</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Legal Enterprise Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  name="legal_name"
                  value={formData.legal_name}
                  onChange={handleChange}
                  placeholder="e.g. Apex Precision Engineering Pvt Ltd"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Trade / Brand Name</label>
                <input
                  type="text"
                  name="trade_name"
                  value={formData.trade_name}
                  onChange={handleChange}
                  placeholder="e.g. Apex Precision"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Legal Entity Type</label>
                <select
                  name="entity_type"
                  value={formData.entity_type}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="PRIVATE_LIMITED">Private Limited Company</option>
                  <option value="PUBLIC_LIMITED">Public Limited Company</option>
                  <option value="LLP">Limited Liability Partnership (LLP)</option>
                  <option value="PARTNERSHIP">Partnership Firm</option>
                  <option value="PROPRIETORSHIP">Sole Proprietorship</option>
                  <option value="COOPERATIVE">Cooperative Society</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Permanent Account Number (PAN) <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  name="pan"
                  value={formData.pan}
                  onChange={handleChange}
                  maxLength={10}
                  placeholder="ABCDE1234F"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white uppercase text-sm focus:outline-none focus:border-blue-500 font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">GSTIN (15 Digits)</label>
                <input
                  type="text"
                  name="gstin"
                  value={formData.gstin}
                  onChange={handleChange}
                  maxLength={15}
                  placeholder="27ABCDE1234F1Z5"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white uppercase text-sm focus:outline-none focus:border-blue-500 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Udyam Registration Number</label>
                <input
                  type="text"
                  name="udyam_number"
                  value={formData.udyam_number}
                  onChange={handleChange}
                  placeholder="UDYAM-MH-01-0012345"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white uppercase text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">MSME Classification</label>
                <select
                  name="msme_category"
                  value={formData.msme_category}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="MICRO">Micro Enterprise (&lt; ₹1 Cr investment)</option>
                  <option value="SMALL">Small Enterprise (&lt; ₹10 Cr investment)</option>
                  <option value="MEDIUM">Medium Enterprise (&lt; ₹50 Cr investment)</option>
                  <option value="LARGE">Large / Non-MSME (&gt; ₹50 Cr investment)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Date of Incorporation</label>
                <input
                  type="date"
                  name="incorporation_date"
                  value={formData.incorporation_date}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 2: Manufacturing & Activity */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Manufacturing Activity & Environmental Categorization</h3>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">NIC 2008 Classification Code</label>
                  <input
                    type="text"
                    name="nic_code"
                    value={formData.nic_code}
                    onChange={handleChange}
                    placeholder="e.g. 28190 (General Purpose Machinery)"
                    className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">Operational Scale</label>
                  <select
                    name="industry_scale"
                    value={formData.industry_scale}
                    onChange={handleChange}
                    className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                  >
                    <option value="COTTAGE">Cottage / Tiny</option>
                    <option value="SMALL_SCALE">Small Scale Unit</option>
                    <option value="MEDIUM_SCALE">Medium Scale Unit</option>
                    <option value="LARGE_SCALE">Large Scale Industry</option>
                    <option value="MEGA">Mega Industrial Project</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Primary Manufacturing Activity <span className="text-rose-400">*</span>
                </label>
                <textarea
                  name="manufacturing_activity"
                  value={formData.manufacturing_activity}
                  onChange={handleChange}
                  rows={2}
                  placeholder="Describe your raw materials, industrial process, and operations..."
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-2">CPCB Pollution Categorization</label>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {[
                    { id: "RED", name: "Red Category", desc: "Pollution Index >= 60", color: "border-red-500 bg-red-950/40 text-red-300" },
                    { id: "ORANGE", name: "Orange Category", desc: "Pollution Index 41-59", color: "border-amber-500 bg-amber-950/40 text-amber-300" },
                    { id: "GREEN", name: "Green Category", desc: "Pollution Index 21-40", color: "border-emerald-500 bg-emerald-950/40 text-emerald-300" },
                    { id: "WHITE", name: "White Category", desc: "Pollution Index <= 20", color: "border-slate-400 bg-slate-800 text-slate-200" },
                  ].map((cat) => (
                    <label
                      key={cat.id}
                      className={`p-3.5 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                        formData.pollution_category === cat.id
                          ? `${cat.color} ring-2 ring-blue-500`
                          : "border-slate-800 bg-slate-900/60 text-slate-400 hover:border-slate-700"
                      }`}
                    >
                      <input
                        type="radio"
                        name="pollution_category"
                        value={cat.id}
                        checked={formData.pollution_category === cat.id}
                        onChange={handleChange}
                        className="sr-only"
                      />
                      <span className="font-semibold text-sm">{cat.name}</span>
                      <span className="text-xs opacity-75 mt-1">{cat.desc}</span>
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Location */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Industrial Plant Location & Geo-Spatial Mapping</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">State <span className="text-rose-400">*</span></label>
                <input
                  type="text"
                  name="state"
                  value={formData.state}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">District <span className="text-rose-400">*</span></label>
                <input
                  type="text"
                  name="district"
                  value={formData.district}
                  onChange={handleChange}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Pincode <span className="text-rose-400">*</span></label>
                <input
                  type="text"
                  name="pincode"
                  value={formData.pincode}
                  onChange={handleChange}
                  maxLength={6}
                  placeholder="411001"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div className="md:col-span-2">
                <label className="block text-xs font-medium text-slate-300 mb-1">Industrial Area / MIDC / GIDC Zone</label>
                <input
                  type="text"
                  name="industrial_area"
                  value={formData.industrial_area}
                  onChange={handleChange}
                  placeholder="e.g. Bhosari Industrial Estate, Phase III"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Plot / Survey No.</label>
                <input
                  type="text"
                  name="plot_number"
                  value={formData.plot_number}
                  onChange={handleChange}
                  placeholder="Plot 42-A"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div className="md:col-span-3">
                <label className="block text-xs font-medium text-slate-300 mb-1">Full Site Address</label>
                <input
                  type="text"
                  name="full_address"
                  value={formData.full_address}
                  onChange={handleChange}
                  placeholder="Complete postal address for physical inspection"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Workforce & Capital */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Workforce, Investment & Utility Demands</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Total Workforce / Employees</label>
                <input
                  type="number"
                  name="total_employees"
                  value={formData.total_employees}
                  onChange={handleChange}
                  min={0}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Plant & Machinery Investment (₹)</label>
                <input
                  type="number"
                  name="plant_machinery_investment"
                  value={formData.plant_machinery_investment}
                  onChange={handleChange}
                  min={0}
                  step={100000}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Land Area (Sq. Meters)</label>
                <input
                  type="number"
                  name="land_area_sqm"
                  value={formData.land_area_sqm}
                  onChange={handleChange}
                  min={0}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Annual Turnover (₹)</label>
                <input
                  type="number"
                  name="annual_turnover"
                  value={formData.annual_turnover}
                  onChange={handleChange}
                  min={0}
                  step={100000}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Connected Power Load (kW)</label>
                <input
                  type="number"
                  name="power_requirement_kw"
                  value={formData.power_requirement_kw}
                  onChange={handleChange}
                  min={0}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Daily Water Demand (KLD)</label>
                <input
                  type="number"
                  name="water_requirement_kld"
                  value={formData.water_requirement_kld}
                  onChange={handleChange}
                  min={0}
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 5: Contact & Final Review */}
        {currentStep === 5 && (
          <div className="space-y-4">
            <h3 className="text-lg font-semibold text-white">Nodal Representative & Verification</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Designated Contact Person <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  name="contact_person"
                  value={formData.contact_person}
                  onChange={handleChange}
                  placeholder="e.g. Smt. Sunita Rao"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Official Mobile Number</label>
                <input
                  type="tel"
                  name="contact_phone"
                  value={formData.contact_phone}
                  onChange={handleChange}
                  placeholder="+919876543210"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">Official Email Address</label>
                <input
                  type="email"
                  name="contact_email"
                  value={formData.contact_email}
                  onChange={handleChange}
                  placeholder="compliance@enterprise.in"
                  className="w-full px-3.5 py-2.5 bg-slate-950/60 border border-slate-700 rounded-lg text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            {/* Summary Review Card */}
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-5 mt-4 space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400">Onboarding Preview</h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div>
                  <span className="text-slate-500 block">Enterprise:</span>
                  <span className="text-white font-medium">{formData.legal_name || "—"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">PAN:</span>
                  <span className="text-white font-mono">{formData.pan.toUpperCase() || "—"}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Category:</span>
                  <span className="text-emerald-400 font-medium">{formData.pollution_category}</span>
                </div>
                <div>
                  <span className="text-slate-500 block">Location:</span>
                  <span className="text-white font-medium">{formData.district}, {formData.state}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Wizard Controls */}
        <div className="flex justify-between items-center pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={handleBack}
            disabled={currentStep === 1}
            className="px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Previous
          </button>

          {currentStep < 5 ? (
            <button
              type="button"
              onClick={handleNext}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-blue-600/30"
            >
              Continue to Step 0{currentStep + 1}
            </button>
          ) : (
            <button
              type="submit"
              disabled={loading}
              className="px-7 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg text-sm font-semibold transition shadow-lg shadow-emerald-600/30 disabled:opacity-50"
            >
              {loading ? "Submitting Registration..." : "Complete Enterprise Onboarding"}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}

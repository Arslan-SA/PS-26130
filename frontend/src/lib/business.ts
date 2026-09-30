/**
 * Business and Industrial Profile types and API client.
 */

import { apiFetch } from "./auth";

export type EntityType = 
  | "PROPRIETORSHIP"
  | "PARTNERSHIP"
  | "LLP"
  | "PRIVATE_LIMITED"
  | "PUBLIC_LIMITED"
  | "COOPERATIVE"
  | "TRUST_SOCIETY"
  | "OTHER";

export type MSMECategory = "MICRO" | "SMALL" | "MEDIUM" | "LARGE";

export type IndustryScale = 
  | "COTTAGE"
  | "SMALL_SCALE"
  | "MEDIUM_SCALE"
  | "LARGE_SCALE"
  | "MEGA";

export type PollutionCategory = "RED" | "ORANGE" | "GREEN" | "WHITE";

export interface BusinessProfile {
  id?: string;
  business_id?: string;
  nic_code?: string | null;
  manufacturing_activity?: string | null;
  products_services?: string | null;
  industry_scale: IndustryScale;
  pollution_category?: PollutionCategory | null;
  state?: string | null;
  district?: string | null;
  city?: string | null;
  pincode?: string | null;
  full_address?: string | null;
  plot_number?: string | null;
  industrial_area?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  total_employees?: number | null;
  plant_machinery_investment?: number | null;
  land_area_sqm?: number | null;
  annual_turnover?: number | null;
  power_requirement_kw?: number | null;
  water_requirement_kld?: number | null;
  contact_person?: string | null;
  contact_phone?: string | null;
  contact_email?: string | null;
  profile_completeness: number;
  is_profile_complete: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface Business {
  id: string;
  user_id: string;
  legal_name: string;
  trade_name?: string | null;
  entity_type: EntityType;
  pan: string;
  gstin?: string | null;
  udyam_number?: string | null;
  cin?: string | null;
  msme_category: MSMECategory;
  incorporation_date?: string | null;
  website?: string | null;
  is_verified: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  profile?: BusinessProfile | null;
}

export interface OnboardingPayload {
  business: {
    legal_name: string;
    trade_name?: string;
    entity_type: EntityType;
    pan: string;
    gstin?: string;
    udyam_number?: string;
    cin?: string;
    msme_category: MSMECategory;
    incorporation_date?: string;
    website?: string;
  };
  profile?: Partial<BusinessProfile>;
}

export interface OnboardingResponse {
  business: Business;
  message: string;
  next_steps: string[];
}

export async function submitOnboarding(payload: OnboardingPayload): Promise<OnboardingResponse> {
  return apiFetch<OnboardingResponse>("/business/onboard", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchUserBusinesses(): Promise<Business[]> {
  return apiFetch<Business[]>("/business/my-businesses");
}

export async function fetchBusinessById(businessId: string): Promise<Business> {
  return apiFetch<Business>(`/business/${businessId}`);
}

export async function updateBusinessProfile(
  businessId: string,
  profile: Partial<BusinessProfile>
): Promise<BusinessProfile> {
  return apiFetch<BusinessProfile>(`/business/${businessId}/profile`, {
    method: "PUT",
    body: JSON.stringify(profile),
  });
}

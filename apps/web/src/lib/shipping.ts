import { apiDelete, apiPatch, apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export type WeightTier = {
  id?: string;
  max_weight_grams: number;
  charge_poisha: number;
};

export type DeliveryZone = {
  id: string;
  slug: string;
  name: string;
  match_districts: string[];
  is_default: boolean;
  is_active: boolean;
  sort_order: number;
  free_shipping_threshold_poisha: number | null;
  created_at: string;
  updated_at: string;
  tiers: WeightTier[];
};

export type DeliveryZoneList = {
  items: DeliveryZone[];
  free_shipping_threshold_poisha: number;
  default_variant_weight_grams: number;
};

export type ShippingQuote = {
  zone_id: string;
  zone_slug: string;
  zone_name: string;
  total_weight_grams: number;
  charge_poisha: number;
  currency: string;
  free_shipping_applied: boolean;
  free_shipping_threshold_poisha: number;
  matched_by: string;
};

export type ZonePayload = {
  slug: string;
  name: string;
  match_districts: string[];
  is_default: boolean;
  is_active: boolean;
  sort_order: number;
  free_shipping_threshold_poisha: number | null;
  tiers: { max_weight_grams: number; charge_poisha: number }[];
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchAdminZones(): Promise<DeliveryZoneList> {
  const response = await fetch("/api/v1/admin/shipping/zones", {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function createZone(payload: ZonePayload): Promise<DeliveryZone> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/admin/shipping/zones", payload, csrf));
}

export async function patchZone(
  id: string,
  payload: Partial<ZonePayload>,
): Promise<DeliveryZone> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPatch(`/api/v1/admin/shipping/zones/${id}`, payload, csrf));
}

export async function deleteZone(id: string): Promise<void> {
  const csrf = await fetchCsrfToken();
  const response = await apiDelete(`/api/v1/admin/shipping/zones/${id}`, csrf);
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

export async function quoteShipping(body: {
  district?: string;
  weight_grams?: number;
  subtotal_poisha?: number;
}): Promise<ShippingQuote> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/shipping/quote", body, csrf));
}

export function poishaToBdtInput(poisha: number | null | undefined): string {
  if (poisha == null) {
    return "";
  }
  return (poisha / 100).toFixed(poisha % 100 === 0 ? 0 : 2);
}

export function bdtInputToPoisha(raw: string): number | null {
  const trimmed = raw.trim();
  if (!trimmed) {
    return null;
  }
  const n = Number.parseFloat(trimmed);
  if (!Number.isFinite(n) || n < 0) {
    return null;
  }
  return Math.round(n * 100);
}

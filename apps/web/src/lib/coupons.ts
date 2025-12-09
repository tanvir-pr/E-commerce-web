import { apiDelete, apiPatch, apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export type Coupon = {
  id: string;
  code: string;
  discount_type: "percent" | "fixed" | string;
  value: number;
  min_spend_poisha: number | null;
  category_id: string | null;
  starts_at: string | null;
  expires_at: string | null;
  max_redemptions: number | null;
  max_per_user: number | null;
  is_active: boolean;
  redemption_count: number;
  created_at: string;
};

export type CouponPayload = {
  code: string;
  discount_type: "percent" | "fixed";
  value: number;
  min_spend_poisha: number | null;
  category_id: string | null;
  starts_at: string | null;
  expires_at: string | null;
  max_redemptions: number | null;
  max_per_user: number | null;
  is_active: boolean;
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchAdminCoupons(): Promise<Coupon[]> {
  const response = await fetch("/api/v1/admin/coupons", {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: Coupon[] }>(response);
  return body.items;
}

export async function createCoupon(payload: CouponPayload): Promise<Coupon> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/admin/coupons", payload, csrf));
}

export async function patchCoupon(id: string, payload: CouponPayload): Promise<Coupon> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPatch(`/api/v1/admin/coupons/${id}`, payload, csrf));
}

export async function deleteCoupon(id: string): Promise<void> {
  const csrf = await fetchCsrfToken();
  const response = await apiDelete(`/api/v1/admin/coupons/${id}`, csrf);
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

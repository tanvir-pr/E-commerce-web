import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";
import type { CheckoutQuoteInput } from "@/lib/checkout";

export type OrderItem = {
  id: string;
  variant_id: string;
  product_id: string;
  product_slug: string;
  product_name: string;
  sku: string;
  size_label: string | null;
  shade_name: string | null;
  spf: number | null;
  qty: number;
  unit_price_poisha: number;
  line_total_poisha: number;
};

export type OrderEvent = {
  id: string;
  from_status: string | null;
  to_status: string;
  actor_user_id: string | null;
  source: string;
  note: string | null;
  created_at: string;
};

export type OrderAddress = {
  id?: string | null;
  label?: string | null;
  line1: string;
  line2?: string | null;
  city: string;
  district?: string | null;
  postal_code?: string | null;
  country?: string;
  phone?: string | null;
};

export type Order = {
  id: string;
  order_number: string;
  status: string;
  currency: string;
  merchandise_subtotal_poisha: number;
  shipping_poisha: number;
  total_poisha: number;
  shipping_zone_slug: string | null;
  shipping_zone_name: string | null;
  total_weight_grams: number;
  shipping_address: OrderAddress;
  payment_method: string | null;
  payment_status: string | null;
  reservation_expires_at: string | null;
  placed_at: string;
  confirmed_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  cancelled_at: string | null;
  items: OrderItem[];
  events: OrderEvent[];
  allowed_transitions: string[];
};

export type OrderSummary = {
  id: string;
  order_number: string;
  status: string;
  total_poisha: number;
  currency: string;
  item_count: number;
  placed_at: string;
  user_email?: string | null;
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function placeOrder(
  body: CheckoutQuoteInput & { payment_method?: string },
): Promise<Order> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/checkout/place", body, csrf));
}

export async function fetchMyOrders(): Promise<OrderSummary[]> {
  const response = await fetch("/api/v1/orders", {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: OrderSummary[] }>(response);
  return body.items;
}

export async function fetchMyOrder(id: string): Promise<Order> {
  const response = await fetch(`/api/v1/orders/${id}`, {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function cancelMyOrder(id: string, note?: string): Promise<Order> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost(`/api/v1/orders/${id}/cancel`, { to_status: "cancelled", note }, csrf));
}

export async function fetchAdminOrders(status = "all"): Promise<OrderSummary[]> {
  const response = await fetch(`/api/v1/admin/orders?status=${encodeURIComponent(status)}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: OrderSummary[] }>(response);
  return body.items;
}

export async function fetchAdminOrder(id: string): Promise<Order> {
  const response = await fetch(`/api/v1/admin/orders/${id}`, {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function transitionAdminOrder(
  id: string,
  toStatus: string,
  note?: string,
): Promise<Order> {
  const csrf = await fetchCsrfToken();
  return okJson(
    await apiPost(`/api/v1/admin/orders/${id}/transition`, { to_status: toStatus, note }, csrf),
  );
}

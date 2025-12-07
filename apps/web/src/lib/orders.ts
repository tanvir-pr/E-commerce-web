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
  courier_name: string | null;
  tracking_number: string | null;
  packed_at: string | null;
  placed_at: string;
  confirmed_at: string | null;
  shipped_at: string | null;
  delivered_at: string | null;
  delivery_failed_at: string | null;
  returned_at: string | null;
  cancelled_at: string | null;
  items: OrderItem[];
  events: OrderEvent[];
  allowed_transitions: string[];
  age_hours?: number | null;
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
  payment_method?: string | null;
  shipping_zone_slug?: string | null;
  courier_name?: string | null;
  tracking_number?: string | null;
  packed_at?: string | null;
  confirmed_at?: string | null;
  shipped_at?: string | null;
  age_hours?: number | null;
};

export type DashboardMetrics = {
  currency: string;
  today: {
    revenue_poisha: number;
    order_count: number;
    aov_poisha: number;
    cod_share: number;
    cancel_rate: number;
  };
  last_7_days: {
    revenue_poisha: number;
    order_count: number;
    aov_poisha: number;
    cod_share: number;
    cancel_rate: number;
  };
  last_30_days: {
    revenue_poisha: number;
    order_count: number;
    aov_poisha: number;
    cod_share: number;
    cancel_rate: number;
  };
  funnel: {
    pending_payment: number;
    confirmed: number;
    shipped: number;
    delivered: number;
    delivery_failed: number;
    returned: number;
    cancelled: number;
  };
  alerts: {
    low_stock_count: number;
    near_expiry_count: number;
    overdue_shipments: number;
    abandoned_cart_value_poisha: number;
  };
  top_products: Array<{
    product_id: string;
    product_slug: string;
    product_name: string;
    units: number;
    revenue_poisha: number;
  }>;
  unshipped_confirmed: number;
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

export type PayStart = {
  order_id: string;
  method: string;
  redirect_url: string;
  provider_ref: string;
  sandbox: boolean;
};

export type PayValidate = {
  order_id: string;
  order_number: string;
  status: string;
  payment_status: string | null;
  provider_ref: string;
  method: string;
};

export async function startOrderPayment(id: string): Promise<PayStart> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost(`/api/v1/orders/${id}/pay`, {}, csrf));
}

export type ReturnRequest = {
  id: string;
  order_id: string;
  order_number?: string | null;
  status: string;
  reason_code: string;
  customer_note: string | null;
  staff_note: string | null;
  refund_poisha: number;
  items: Array<{ id: string; order_item_id: string; qty: number; unit_price_poisha: number }>;
  created_at: string;
};

export async function createReturnRequest(
  orderId: string,
  body: {
    reason_code: string;
    customer_note?: string;
    items: Array<{ order_item_id: string; qty: number }>;
  },
): Promise<ReturnRequest> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost(`/api/v1/orders/${orderId}/returns`, body, csrf));
}

export async function fetchAdminReturns(status = "pending"): Promise<ReturnRequest[]> {
  const response = await fetch(`/api/v1/admin/returns?status=${encodeURIComponent(status)}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: ReturnRequest[] }>(response);
  return body.items;
}

export async function approveAdminReturn(id: string, staffNote?: string): Promise<ReturnRequest> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost(`/api/v1/admin/returns/${id}/approve`, { staff_note: staffNote }, csrf));
}

export async function rejectAdminReturn(id: string, staffNote: string): Promise<ReturnRequest> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost(`/api/v1/admin/returns/${id}/reject`, { staff_note: staffNote }, csrf));
}

export async function validatePayment(
  method: string,
  body: Record<string, unknown>,
): Promise<PayValidate> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost(`/api/v1/payments/${method}/validate`, body, csrf));
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

export async function packAdminOrder(id: string, note?: string): Promise<Order> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost(`/api/v1/admin/orders/${id}/pack`, { note }, csrf));
}

export async function transitionAdminOrder(
  id: string,
  toStatus: string,
  opts?: { note?: string; courier_name?: string; tracking_number?: string },
): Promise<Order> {
  const csrf = await fetchCsrfToken();
  return okJson(
    await apiPost(
      `/api/v1/admin/orders/${id}/transition`,
      {
        to_status: toStatus,
        note: opts?.note,
        courier_name: opts?.courier_name,
        tracking_number: opts?.tracking_number,
      },
      csrf,
    ),
  );
}

export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
  const response = await fetch("/api/v1/admin/metrics", {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

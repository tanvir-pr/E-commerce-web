import { apiDelete, apiPatch, apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export type CartItem = {
  id: string;
  variant_id: string;
  product_id: string;
  product_slug: string;
  product_name: string;
  size_label: string | null;
  shade_name: string | null;
  spf: number | null;
  sku: string;
  qty: number;
  unit_price_poisha: number;
  line_total_poisha: number;
  routine_step: string | null;
  category_slug: string | null;
  qty_available: number | null;
};

export type Cart = {
  id: string;
  status: string;
  item_count: number;
  subtotal_poisha: number;
  currency: string;
  is_guest: boolean;
  updated_at: string;
  last_activity_at: string;
  items: CartItem[];
};

export type UpsellItem = {
  product_id: string;
  slug: string;
  name: string;
  subtitle: string | null;
  category_slug: string;
  from_price_poisha: number | null;
  reason: string;
};

export type Upsell = {
  items: UpsellItem[];
  missing_steps: string[];
};

export type AdminCartSummary = {
  id: string;
  status: string;
  user_id: string | null;
  user_email: string | null;
  is_guest: boolean;
  item_count: number;
  subtotal_poisha: number;
  last_activity_at: string;
  created_at: string;
  abandoned_at: string | null;
  cleared_at: string | null;
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchCart(): Promise<Cart> {
  const response = await fetch("/api/v1/cart", {
    credentials: "include",
    cache: "no-store",
  });
  return okJson<Cart>(response);
}

export async function addToCart(variantId: string, qty = 1): Promise<Cart> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/cart/items", { variant_id: variantId, qty }, csrf));
}

export async function patchCartItem(itemId: string, qty: number): Promise<Cart> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPatch(`/api/v1/cart/items/${itemId}`, { qty }, csrf));
}

export async function removeCartItem(itemId: string): Promise<Cart> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiDelete(`/api/v1/cart/items/${itemId}`, csrf));
}

export async function clearCart(): Promise<Cart> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiDelete("/api/v1/cart", csrf));
}

export async function fetchUpsell(): Promise<Upsell> {
  const response = await fetch("/api/v1/cart/upsell", {
    credentials: "include",
    cache: "no-store",
  });
  return okJson<Upsell>(response);
}

export async function fetchAdminCarts(status = "all"): Promise<{
  items: AdminCartSummary[];
  abandon_after_hours: number;
}> {
  const response = await fetch(`/api/v1/admin/carts?status=${encodeURIComponent(status)}`, {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function fetchAdminCart(id: string): Promise<AdminCartSummary & { items: CartItem[] }> {
  const response = await fetch(`/api/v1/admin/carts/${id}`, {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function clearAdminCart(id: string): Promise<void> {
  const csrf = await fetchCsrfToken();
  const response = await apiDelete(`/api/v1/admin/carts/${id}`, csrf);
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";
import type { Cart } from "@/lib/cart";
import type { ShippingQuote } from "@/lib/shipping";

export type CheckoutAddress = {
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

export type CheckoutStockLine = {
  variant_id: string;
  sku: string;
  qty: number;
  qty_available: number | null;
  ok: boolean;
  message: string | null;
};

export type CheckoutQuote = {
  cart: Cart;
  address: CheckoutAddress;
  shipping: ShippingQuote;
  stock: CheckoutStockLine[];
  contact: {
    email_verified: boolean;
    phone_verified: boolean;
    ok: boolean;
  };
  merchandise_subtotal_poisha: number;
  shipping_poisha: number;
  discount_poisha: number;
  total_poisha: number;
  currency: string;
  coupon_code: string | null;
  coupon_id: string | null;
  coupon_message: string | null;
  ready: boolean;
  blockers: string[];
  quoted_at: string;
  place_order_available: boolean;
};

export type CheckoutQuoteInput = {
  address_id?: string;
  line1?: string;
  line2?: string;
  city?: string;
  district?: string;
  postal_code?: string;
  country?: string;
  phone?: string;
  label?: string;
  coupon_code?: string;
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchCheckoutQuote(body: CheckoutQuoteInput): Promise<CheckoutQuote> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/checkout/quote", body, csrf));
}

export async function repriceCheckout(body: CheckoutQuoteInput): Promise<CheckoutQuote> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/checkout/reprice", body, csrf));
}

import { apiDelete, apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export type WishlistItem = {
  id: string;
  product_id: string;
  product_slug: string;
  product_name: string;
  subtitle: string | null;
  from_price_poisha: number | null;
  created_at: string;
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchWishlist(): Promise<WishlistItem[]> {
  const response = await fetch("/api/v1/wishlist", {
    credentials: "include",
    cache: "no-store",
  });
  if (response.status === 401) {
    return [];
  }
  const body = await okJson<{ items: WishlistItem[] }>(response);
  return body.items;
}

export async function addToWishlist(productId: string): Promise<WishlistItem> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/wishlist", { product_id: productId }, csrf));
}

export async function removeFromWishlist(productId: string): Promise<void> {
  const csrf = await fetchCsrfToken();
  const response = await apiDelete(`/api/v1/wishlist/${productId}`, csrf);
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

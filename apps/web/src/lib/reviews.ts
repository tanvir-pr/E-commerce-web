import { apiPatch, apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export type Review = {
  id: string;
  product_id: string;
  product_slug: string | null;
  product_name: string | null;
  rating: number;
  title: string | null;
  body: string;
  skin_type: string | null;
  is_verified: boolean;
  is_published: boolean;
  created_at: string;
  author_display: string | null;
};

export type ReviewList = {
  items: Review[];
  rating_avg: number | null;
  rating_count: number;
  can_review: boolean;
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchProductReviews(slug: string): Promise<ReviewList> {
  const response = await fetch(`/api/v1/catalog/products/${encodeURIComponent(slug)}/reviews`, {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function createProductReview(
  slug: string,
  body: { rating: number; title?: string; body: string; skin_type?: string },
): Promise<Review> {
  const csrf = await fetchCsrfToken();
  return okJson(
    await apiPost(`/api/v1/catalog/products/${encodeURIComponent(slug)}/reviews`, body, csrf),
  );
}

export async function fetchAdminReviews(published?: boolean): Promise<Review[]> {
  const query =
    published === undefined ? "" : `?published=${published ? "true" : "false"}`;
  const response = await fetch(`/api/v1/admin/reviews${query}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<ReviewList>(response);
  return body.items;
}

export async function moderateReview(
  id: string,
  is_published: boolean,
): Promise<Review> {
  const csrf = await fetchCsrfToken();
  return okJson(
    await apiPatch(`/api/v1/admin/reviews/${id}`, { is_published }, csrf),
  );
}

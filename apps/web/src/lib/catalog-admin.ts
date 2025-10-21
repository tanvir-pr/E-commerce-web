import { apiDelete, apiPatch, apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export type ProductStatus = "draft" | "published" | "archived";
export type RoutineStep = "am" | "pm" | "both";

export type CategoryNode = {
  id: string;
  parent_id: string | null;
  slug: string;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  attribute_ids: string[];
  children: CategoryNode[];
};

export type Attribute = {
  id: string;
  kind: string;
  slug: string;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
};

export type ProductSummary = {
  id: string;
  category_id: string;
  category_slug: string | null;
  slug: string;
  name: string;
  subtitle: string | null;
  routine_step: string | null;
  status: ProductStatus;
  from_price_poisha: number | null;
  published_at: string | null;
};

export type Variant = {
  id: string;
  sku: string;
  size_label: string | null;
  shade_name: string | null;
  shade_hex: string | null;
  spf: number | null;
  price_poisha: number;
  compare_at_poisha: number | null;
  barcode: string | null;
  weight_grams: number | null;
  is_active: boolean;
  sort_order: number;
};

export type ProductImage = {
  id: string;
  slot: string;
  alt_text: string | null;
  sort_order: number;
  width: number;
  height: number;
  thumb_webp_url: string | null;
  card_webp_url: string | null;
  full_webp_url: string | null;
};

export type ProductDetail = {
  id: string;
  category_id: string;
  category_slug: string | null;
  slug: string;
  name: string;
  subtitle: string | null;
  description: string | null;
  how_to_use: string | null;
  ingredients_text: string | null;
  warnings: string | null;
  routine_step: string | null;
  pao_months: number | null;
  shelf_life_months: number | null;
  status: ProductStatus;
  published_at: string | null;
  attributes: { id: string; kind: string; slug: string; name: string }[];
  variants: Variant[];
  images: ProductImage[];
};

export type LowStockItem = {
  variant_id: string;
  sku: string;
  product_id: string;
  product_slug: string | null;
  qty_on_hand: number;
  nearest_expiry: string | null;
};

export function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

export function formatBdt(poisha: number | null | undefined): string {
  if (poisha == null) {
    return "—";
  }
  return `৳${(poisha / 100).toFixed(2)}`;
}

export function bdtToPoisha(bdt: string): number {
  const n = Number.parseFloat(bdt);
  if (!Number.isFinite(n) || n < 0) {
    return 0;
  }
  return Math.round(n * 100);
}

export function poishaToBdtInput(poisha: number | null | undefined): string {
  if (poisha == null) {
    return "";
  }
  return (poisha / 100).toFixed(2);
}

export function flattenCategories(nodes: CategoryNode[]): CategoryNode[] {
  const out: CategoryNode[] = [];
  const walk = (list: CategoryNode[], depth = 0) => {
    for (const node of list) {
      out.push({ ...node, name: `${"— ".repeat(depth)}${node.name}` });
      if (node.children?.length) {
        walk(node.children, depth + 1);
      }
    }
  };
  walk(nodes);
  return out;
}

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchAdminCategories(): Promise<CategoryNode[]> {
  const response = await fetch("/api/v1/admin/catalog/categories", {
    credentials: "include",
    cache: "no-store",
  });
  return okJson<CategoryNode[]>(response);
}

export async function fetchAdminAttributes(): Promise<Attribute[]> {
  const response = await fetch("/api/v1/admin/catalog/attributes", {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: Attribute[] }>(response);
  return body.items;
}

export async function fetchAdminProducts(params?: {
  status?: string;
  category_id?: string;
}): Promise<ProductSummary[]> {
  const query = new URLSearchParams();
  if (params?.status) {
    query.set("status", params.status);
  }
  if (params?.category_id) {
    query.set("category_id", params.category_id);
  }
  const suffix = query.toString() ? `?${query}` : "";
  const response = await fetch(`/api/v1/admin/catalog/products${suffix}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: ProductSummary[] }>(response);
  return body.items;
}

export async function fetchAdminProduct(id: string): Promise<ProductDetail> {
  const response = await fetch(`/api/v1/admin/catalog/products/${id}`, {
    credentials: "include",
    cache: "no-store",
  });
  return okJson<ProductDetail>(response);
}

export async function fetchLowStock(threshold = 10): Promise<LowStockItem[]> {
  const response = await fetch(`/api/v1/admin/inventory/low-stock?threshold=${threshold}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: LowStockItem[] }>(response);
  return body.items;
}

export async function createCategory(payload: unknown): Promise<CategoryNode> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/admin/catalog/categories", payload, csrf));
}

export async function patchCategory(id: string, payload: unknown): Promise<CategoryNode> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPatch(`/api/v1/admin/catalog/categories/${id}`, payload, csrf));
}

export async function deleteCategory(id: string): Promise<void> {
  const csrf = await fetchCsrfToken();
  const response = await apiDelete(`/api/v1/admin/catalog/categories/${id}`, csrf);
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

export async function createProduct(payload: unknown): Promise<ProductDetail> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/admin/catalog/products", payload, csrf));
}

export async function patchProduct(id: string, payload: unknown): Promise<ProductDetail> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPatch(`/api/v1/admin/catalog/products/${id}`, payload, csrf));
}

export async function deleteProduct(id: string): Promise<void> {
  const csrf = await fetchCsrfToken();
  const response = await apiDelete(`/api/v1/admin/catalog/products/${id}`, csrf);
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

export async function bulkProductStatus(
  productIds: string[],
  status: ProductStatus,
): Promise<{ updated: number; status: ProductStatus }> {
  const csrf = await fetchCsrfToken();
  return okJson(
    await apiPost(
      "/api/v1/admin/catalog/products/bulk-status",
      { product_ids: productIds, status },
      csrf,
    ),
  );
}

export async function addVariant(productId: string, payload: unknown): Promise<Variant> {
  const csrf = await fetchCsrfToken();
  return okJson(
    await apiPost(`/api/v1/admin/catalog/products/${productId}/variants`, payload, csrf),
  );
}

export async function patchVariant(variantId: string, payload: unknown): Promise<Variant> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPatch(`/api/v1/admin/catalog/variants/${variantId}`, payload, csrf));
}

export async function deleteVariant(variantId: string): Promise<void> {
  const csrf = await fetchCsrfToken();
  const response = await apiDelete(`/api/v1/admin/catalog/variants/${variantId}`, csrf);
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

export async function uploadProductImage(
  productId: string,
  file: File,
  slot: string,
  altText: string,
): Promise<void> {
  const csrf = await fetchCsrfToken();
  const form = new FormData();
  form.append("file", file);
  form.append("slot", slot);
  if (altText) {
    form.append("alt_text", altText);
  }
  const response = await fetch(`/api/v1/admin/catalog/products/${productId}/images`, {
    method: "POST",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "X-CSRF-Token": csrf,
    },
    body: form,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

export async function deleteProductImage(imageId: string): Promise<void> {
  const csrf = await fetchCsrfToken();
  const response = await apiDelete(`/api/v1/admin/catalog/images/${imageId}`, csrf);
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

export async function receiveStock(payload: {
  variant_id: string;
  qty: number;
  lot_code?: string;
  expires_on?: string;
  note?: string;
}): Promise<void> {
  const csrf = await fetchCsrfToken();
  const response = await apiPost("/api/v1/admin/inventory/receipts", payload, csrf);
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
}

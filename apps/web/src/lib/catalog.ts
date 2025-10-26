export type PublicCategory = {
  id: string;
  parent_id: string | null;
  slug: string;
  name: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  children: PublicCategory[];
};

export type PublicProductSummary = {
  id: string;
  category_id: string;
  category_slug: string | null;
  slug: string;
  name: string;
  subtitle: string | null;
  routine_step: string | null;
  status: string;
  from_price_poisha: number | null;
  published_at: string | null;
};

export type PublicVariant = {
  id: string;
  sku: string;
  size_label: string | null;
  shade_name: string | null;
  shade_hex: string | null;
  spf: number | null;
  price_poisha: number;
  compare_at_poisha: number | null;
  is_active: boolean;
  sort_order: number;
};

export type PublicProductImage = {
  id: string;
  slot: string;
  alt_text: string | null;
  sort_order: number;
  thumb_webp_url: string | null;
  card_webp_url: string | null;
  full_webp_url: string | null;
};

export type PublicProduct = {
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
  status: string;
  attributes: { id: string; kind: string; slug: string; name: string }[];
  variants: PublicVariant[];
  images: PublicProductImage[];
};

export function formatBdt(poisha: number | null | undefined): string {
  if (poisha == null) {
    return "—";
  }
  return `৳${(poisha / 100).toLocaleString("en-BD", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

export function leafCategories(tree: PublicCategory[]): PublicCategory[] {
  const leaves: PublicCategory[] = [];
  const walk = (nodes: PublicCategory[]) => {
    for (const node of nodes) {
      if (!node.is_active) {
        continue;
      }
      if (node.children?.length) {
        walk(node.children);
      } else {
        leaves.push(node);
      }
    }
  };
  walk(tree);
  return leaves.sort((a, b) => a.sort_order - b.sort_order || a.name.localeCompare(b.name));
}

export async function fetchCategories(): Promise<PublicCategory[]> {
  const response = await fetch("/api/v1/catalog/categories?tree=true", {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("categories");
  }
  return (await response.json()) as PublicCategory[];
}

export async function fetchCategory(slug: string): Promise<PublicCategory | null> {
  const response = await fetch(`/api/v1/catalog/categories/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error("category");
  }
  return (await response.json()) as PublicCategory;
}

export async function fetchProducts(params?: {
  category?: string;
}): Promise<PublicProductSummary[]> {
  const query = new URLSearchParams();
  if (params?.category) {
    query.set("category", params.category);
  }
  const suffix = query.toString() ? `?${query}` : "";
  const response = await fetch(`/api/v1/catalog/products${suffix}`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("products");
  }
  const body = (await response.json()) as { items: PublicProductSummary[] };
  return body.items;
}

export async function fetchProduct(slug: string): Promise<PublicProduct | null> {
  const response = await fetch(`/api/v1/catalog/products/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });
  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error("product");
  }
  return (await response.json()) as PublicProduct;
}

/** Server-side fetch via internal API URL (RSC). */
export async function serverFetchCategories(): Promise<PublicCategory[]> {
  const base = (process.env.API_INTERNAL_URL || process.env.API_URL || "http://localhost:8000").replace(
    /\/$/,
    "",
  );
  const response = await fetch(`${base}/api/v1/catalog/categories?tree=true`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return [];
  }
  return (await response.json()) as PublicCategory[];
}

export async function serverFetchProducts(params?: {
  category?: string;
}): Promise<PublicProductSummary[]> {
  const base = (process.env.API_INTERNAL_URL || process.env.API_URL || "http://localhost:8000").replace(
    /\/$/,
    "",
  );
  const query = new URLSearchParams();
  if (params?.category) {
    query.set("category", params.category);
  }
  const suffix = query.toString() ? `?${query}` : "";
  const response = await fetch(`${base}/api/v1/catalog/products${suffix}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return [];
  }
  const body = (await response.json()) as { items: PublicProductSummary[] };
  return body.items;
}

export async function serverFetchCategory(slug: string): Promise<PublicCategory | null> {
  const base = (process.env.API_INTERNAL_URL || process.env.API_URL || "http://localhost:8000").replace(
    /\/$/,
    "",
  );
  const response = await fetch(`${base}/api/v1/catalog/categories/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as PublicCategory;
}

export async function serverFetchProduct(slug: string): Promise<PublicProduct | null> {
  const base = (process.env.API_INTERNAL_URL || process.env.API_URL || "http://localhost:8000").replace(
    /\/$/,
    "",
  );
  const response = await fetch(`${base}/api/v1/catalog/products/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as PublicProduct;
}

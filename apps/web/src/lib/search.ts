export type SearchSort = "relevance" | "name_asc" | "name_desc" | "price_asc" | "price_desc";

export type FacetValue = { value: string; count: number };

export type SearchHit = {
  id: string;
  slug: string;
  name: string;
  subtitle: string | null;
  category_slug: string | null;
  category_name: string | null;
  routine_step: string | null;
  from_price_poisha: number | null;
  skin_types: string[];
  concerns: string[];
  ingredients: string[];
};

export type SearchResult = {
  query: string;
  total: number;
  offset: number;
  limit: number;
  sort: SearchSort;
  processing_time_ms: number | null;
  items: SearchHit[];
  facets: Record<string, FacetValue[]>;
};

export type SuggestHit = {
  slug: string;
  name: string;
  subtitle: string | null;
  category_slug: string | null;
  from_price_poisha: number | null;
};

export type SearchParams = {
  q?: string;
  concern?: string;
  ingredient?: string;
  skin_type?: string;
  category?: string;
  min_price_bdt?: string;
  max_price_bdt?: string;
  sort?: SearchSort;
  offset?: number;
};

function bdtToPoisha(value: string | undefined): number | undefined {
  if (!value?.trim()) {
    return undefined;
  }
  const n = Number.parseFloat(value);
  if (!Number.isFinite(n) || n < 0) {
    return undefined;
  }
  return Math.round(n * 100);
}

export function buildSearchQuery(params: SearchParams): string {
  const query = new URLSearchParams();
  if (params.q?.trim()) {
    query.set("q", params.q.trim());
  }
  if (params.concern) {
    query.set("concern", params.concern);
  }
  if (params.ingredient) {
    query.set("ingredient", params.ingredient);
  }
  if (params.skin_type) {
    query.set("skin_type", params.skin_type);
  }
  if (params.category) {
    query.set("category", params.category);
  }
  const minP = bdtToPoisha(params.min_price_bdt);
  const maxP = bdtToPoisha(params.max_price_bdt);
  if (minP != null) {
    query.set("min_price_poisha", String(minP));
  }
  if (maxP != null) {
    query.set("max_price_poisha", String(maxP));
  }
  if (params.sort && params.sort !== "relevance") {
    query.set("sort", params.sort);
  }
  if (params.offset && params.offset > 0) {
    query.set("offset", String(params.offset));
  }
  return query.toString();
}

export async function fetchSearch(params: SearchParams): Promise<SearchResult> {
  const qs = buildSearchQuery(params);
  const response = await fetch(`/api/v1/search${qs ? `?${qs}` : ""}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("search");
  }
  return (await response.json()) as SearchResult;
}

export async function fetchSuggest(q: string): Promise<SuggestHit[]> {
  if (q.trim().length < 2) {
    return [];
  }
  const response = await fetch(`/api/v1/search/suggest?q=${encodeURIComponent(q.trim())}&limit=8`, {
    cache: "no-store",
  });
  if (!response.ok) {
    return [];
  }
  const body = (await response.json()) as { items: SuggestHit[] };
  return body.items;
}

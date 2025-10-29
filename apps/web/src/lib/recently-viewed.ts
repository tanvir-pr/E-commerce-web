const KEY = "solum.recentlyViewed.v1";
const MAX = 8;

export type RecentProduct = {
  slug: string;
  name: string;
  subtitle?: string | null;
  from_price_poisha?: number | null;
  viewedAt: number;
};

export function readRecentlyViewed(): RecentProduct[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) {
      return [];
    }
    const parsed = JSON.parse(raw) as RecentProduct[];
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed
      .filter((row) => row && typeof row.slug === "string" && typeof row.name === "string")
      .slice(0, MAX);
  } catch {
    return [];
  }
}

export function recordRecentlyViewed(entry: Omit<RecentProduct, "viewedAt">): void {
  if (typeof window === "undefined") {
    return;
  }
  const next: RecentProduct[] = [
    { ...entry, viewedAt: Date.now() },
    ...readRecentlyViewed().filter((row) => row.slug !== entry.slug),
  ].slice(0, MAX);
  try {
    window.localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // ignore quota errors
  }
}

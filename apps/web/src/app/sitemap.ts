import type { MetadataRoute } from "next";
import { leafCategories, serverFetchCategories, serverFetchProducts } from "@/lib/catalog";
import { routing } from "@/i18n/routing";
import { absoluteUrl } from "@/lib/site";

const STATIC_PATHS = [
  "",
  "/shop",
  "/search",
  "/privacy",
  "/terms",
  "/shipping",
  "/returns",
] as const;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [categories, products] = await Promise.all([
    serverFetchCategories(),
    serverFetchProducts(),
  ]);
  const leaves = leafCategories(categories);
  const now = new Date();
  const entries: MetadataRoute.Sitemap = [];

  for (const locale of routing.locales) {
    for (const path of STATIC_PATHS) {
      entries.push({
        url: absoluteUrl(locale, path),
        lastModified: now,
        changeFrequency: path === "" || path === "/shop" ? "daily" : "monthly",
        priority: path === "" ? 1 : path === "/shop" ? 0.9 : 0.5,
      });
    }
    for (const category of leaves) {
      entries.push({
        url: absoluteUrl(locale, `/c/${category.slug}`),
        lastModified: now,
        changeFrequency: "weekly",
        priority: 0.8,
      });
    }
    for (const product of products) {
      entries.push({
        url: absoluteUrl(locale, `/p/${product.slug}`),
        lastModified: product.published_at ? new Date(product.published_at) : now,
        changeFrequency: "weekly",
        priority: 0.85,
      });
    }
  }

  return entries;
}

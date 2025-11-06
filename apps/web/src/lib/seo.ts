import type { Metadata } from "next";
import type { PublicProduct } from "@/lib/catalog";
import { absoluteAssetUrl, absoluteUrl, languageAlternates, siteUrl } from "@/lib/site";

const BRAND = "Solum";

export function truncate(text: string, max = 160): string {
  const compact = text.replace(/\s+/g, " ").trim();
  if (compact.length <= max) {
    return compact;
  }
  return `${compact.slice(0, max - 1).trimEnd()}…`;
}

export function pageMetadata({
  locale,
  path,
  title,
  description,
  image,
  type = "website",
  noIndex = false,
}: {
  locale: string;
  path: string;
  title: string;
  description: string;
  image?: string | null;
  type?: "website" | "article";
  noIndex?: boolean;
}): Metadata {
  const url = absoluteUrl(locale, path);
  const desc = truncate(description);
  const ogImage = absoluteAssetUrl(image ?? null);
  return {
    metadataBase: new URL(siteUrl()),
    title: { absolute: title },
    description: desc,
    alternates: {
      canonical: url,
      languages: languageAlternates(path),
    },
    openGraph: {
      type,
      locale: locale === "bn" ? "bn_BD" : "en_BD",
      url,
      siteName: BRAND,
      title,
      description: desc,
      ...(ogImage
        ? {
            images: [{ url: ogImage, alt: title }],
          }
        : {}),
    },
    twitter: {
      card: ogImage ? "summary_large_image" : "summary",
      title,
      description: desc,
      ...(ogImage ? { images: [ogImage] } : {}),
    },
    robots: noIndex ? { index: false, follow: false } : { index: true, follow: true },
  };
}

export function productJsonLd(product: PublicProduct, locale: string): Record<string, unknown> {
  const active = product.variants.filter((v) => v.is_active);
  const prices = active.map((v) => v.price_poisha);
  const low = prices.length ? Math.min(...prices) : null;
  const high = prices.length ? Math.max(...prices) : null;
  const image =
    product.images.find((i) => i.slot === "product")?.full_webp_url ??
    product.images[0]?.full_webp_url ??
    null;
  const url = absoluteUrl(locale, `/p/${product.slug}`);
  const description = truncate(
    product.description || product.subtitle || `${product.name} — ${BRAND}`,
    500,
  );

  const offers =
    active.length === 0
      ? undefined
      : active.length === 1
        ? {
            "@type": "Offer",
            url,
            priceCurrency: "BDT",
            price: (active[0].price_poisha / 100).toFixed(2),
            availability: "https://schema.org/InStock",
            itemCondition: "https://schema.org/NewCondition",
          }
        : {
            "@type": "AggregateOffer",
            url,
            priceCurrency: "BDT",
            lowPrice: low != null ? (low / 100).toFixed(2) : undefined,
            highPrice: high != null ? (high / 100).toFixed(2) : undefined,
            offerCount: active.length,
            availability: "https://schema.org/InStock",
          };

  return {
    "@context": "https://schema.org",
    "@type": "Product",
    name: product.name,
    description,
    sku: active[0]?.sku,
    url,
    brand: { "@type": "Brand", name: BRAND },
    category: product.category_slug ?? undefined,
    image: absoluteAssetUrl(image),
    ...(offers ? { offers } : {}),
  };
}

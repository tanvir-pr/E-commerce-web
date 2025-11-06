import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { ProductDetail } from "@/components/storefront/ProductDetail";
import { JsonLd } from "@/components/seo/JsonLd";
import { serverFetchProduct } from "@/lib/catalog";
import { pageMetadata, productJsonLd, truncate } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  const product = await serverFetchProduct(slug);
  if (!product) {
    const t = await getTranslations({ locale, namespace: "notFound" });
    return pageMetadata({
      locale,
      path: `/p/${slug}`,
      title: `${t("title")} · Solum`,
      description: t("title"),
      noIndex: true,
    });
  }
  const description = truncate(
    product.description || product.subtitle || `${product.name} — Solum skincare`,
  );
  const image =
    product.images.find((i) => i.slot === "product")?.full_webp_url ??
    product.images[0]?.full_webp_url ??
    null;
  return pageMetadata({
    locale,
    path: `/p/${product.slug}`,
    title: `${product.name} · Solum`,
    description,
    image,
  });
}

export default async function ProductPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const product = await serverFetchProduct(slug);
  if (!product) {
    notFound();
  }
  return (
    <main id="main">
      <JsonLd data={productJsonLd(product, locale)} />
      <ProductDetail product={product} locale={locale} />
    </main>
  );
}

import { notFound } from "next/navigation";
import { setRequestLocale } from "next-intl/server";
import { ProductDetail } from "@/components/storefront/ProductDetail";
import { serverFetchProduct } from "@/lib/catalog";

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
      <ProductDetail product={product} locale={locale} />
    </main>
  );
}

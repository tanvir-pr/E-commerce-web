import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { CategoryStrip } from "@/components/storefront/CategoryStrip";
import { FeaturedProducts } from "@/components/storefront/FeaturedProducts";
import { HomeHero } from "@/components/storefront/HomeHero";
import { HomeStatus } from "@/components/storefront/HomeStatus";
import { serverFetchCategories, serverFetchProducts } from "@/lib/catalog";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "meta" });
  return pageMetadata({
    locale,
    path: "",
    title: t("title"),
    description: t("description"),
  });
}

export default async function HomePage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const [categories, products] = await Promise.all([
    serverFetchCategories(),
    serverFetchProducts(),
  ]);

  return (
    <main id="main">
      <HomeHero locale={locale} />
      <CategoryStrip locale={locale} categories={categories} />
      <FeaturedProducts locale={locale} products={products} />
      <HomeStatus />
    </main>
  );
}

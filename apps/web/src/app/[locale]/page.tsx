import { setRequestLocale } from "next-intl/server";
import { CategoryStrip } from "@/components/storefront/CategoryStrip";
import { FeaturedProducts } from "@/components/storefront/FeaturedProducts";
import { HomeHero } from "@/components/storefront/HomeHero";
import { HomeStatus } from "@/components/storefront/HomeStatus";
import { serverFetchCategories, serverFetchProducts } from "@/lib/catalog";

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

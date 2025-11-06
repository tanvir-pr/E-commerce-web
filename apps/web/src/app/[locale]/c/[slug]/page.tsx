import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Reveal } from "@/components/motion/Reveal";
import { ProductTile } from "@/components/storefront/ProductTile";
import { serverFetchCategory, serverFetchProducts } from "@/lib/catalog";
import { pageMetadata, truncate } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}): Promise<Metadata> {
  const { locale, slug } = await params;
  const t = await getTranslations({ locale, namespace: "storefront" });
  const category = await serverFetchCategory(slug);
  if (!category) {
    return pageMetadata({
      locale,
      path: `/c/${slug}`,
      title: `${t("shop")} · Solum`,
      description: t("categoryFallbackLede"),
      noIndex: true,
    });
  }
  return pageMetadata({
    locale,
    path: `/c/${category.slug}`,
    title: `${category.name} · Solum`,
    description: truncate(category.description || t("categoryFallbackLede")),
  });
}

export default async function CategoryPage({
  params,
}: {
  params: Promise<{ locale: string; slug: string }>;
}) {
  const { locale, slug } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("storefront");
  const category = await serverFetchCategory(slug);
  if (!category) {
    notFound();
  }
  const products = await serverFetchProducts({ category: slug });

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-md py-xl">
      <p className="text-sm text-muted">
        <Link href={`/${locale}/shop`} className="underline">
          {t("shop")}
        </Link>
      </p>
      <Reveal>
        <h1 className="mt-md font-display text-hero text-ink">{category.name}</h1>
        {category.description ? (
          <p className="mt-sm max-w-2xl text-muted">{category.description}</p>
        ) : (
          <p className="mt-sm max-w-2xl text-muted">{t("categoryFallbackLede")}</p>
        )}
      </Reveal>
      <Reveal className="mt-xl">
        {products.length === 0 ? (
          <p className="text-sm text-muted">{t("emptyProducts")}</p>
        ) : (
          <div className="divide-y divide-line border-t border-line">
            {products.map((product, index) => (
              <ProductTile key={product.id} product={product} locale={locale} index={index} />
            ))}
          </div>
        )}
      </Reveal>
    </main>
  );
}

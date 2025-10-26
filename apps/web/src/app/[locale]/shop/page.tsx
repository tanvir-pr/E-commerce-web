import Link from "next/link";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { Reveal } from "@/components/motion/Reveal";
import { ProductTile } from "@/components/storefront/ProductTile";
import { leafCategories, serverFetchCategories, serverFetchProducts } from "@/lib/catalog";

export default async function ShopPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("storefront");
  const [categories, products] = await Promise.all([
    serverFetchCategories(),
    serverFetchProducts(),
  ]);
  const leaves = leafCategories(categories);

  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-md py-xl">
      <Reveal>
        <h1 className="font-display text-hero text-ink">{t("shopTitle")}</h1>
        <p className="mt-sm max-w-xl text-muted">{t("shopLede")}</p>
      </Reveal>

      <Reveal className="mt-xl">
        <nav className="flex flex-wrap gap-sm text-sm">
          {leaves.map((cat) => (
            <Link
              key={cat.id}
              href={`/${locale}/c/${cat.slug}`}
              className="border-b border-line pb-2xs text-muted hover:border-sage hover:text-ink"
            >
              {cat.name}
            </Link>
          ))}
        </nav>
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

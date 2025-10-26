import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Reveal } from "@/components/motion/Reveal";
import { ProductTile } from "@/components/storefront/ProductTile";
import type { PublicProductSummary } from "@/lib/catalog";

export async function FeaturedProducts({
  locale,
  products,
}: {
  locale: string;
  products: PublicProductSummary[];
}) {
  const t = await getTranslations("storefront");
  const featured = products.slice(0, 6);

  return (
    <section className="mx-auto w-full max-w-6xl px-md pb-3xl">
      <Reveal>
        <div className="flex flex-wrap items-end justify-between gap-md">
          <div>
            <h2 className="font-display text-display text-ink">{t("featuredTitle")}</h2>
            <p className="mt-sm max-w-lg text-muted">{t("featuredLede")}</p>
          </div>
          <Link href={`/${locale}/shop`} className="text-sm text-sage underline">
            {t("viewAll")}
          </Link>
        </div>
      </Reveal>
      <Reveal className="mt-lg">
        {featured.length === 0 ? (
          <p className="text-sm text-muted">{t("emptyProducts")}</p>
        ) : (
          <div className="divide-y divide-line border-t border-line">
            {featured.map((product, index) => (
              <ProductTile key={product.id} product={product} locale={locale} index={index} />
            ))}
          </div>
        )}
      </Reveal>
    </section>
  );
}

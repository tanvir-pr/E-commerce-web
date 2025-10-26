import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { Reveal } from "@/components/motion/Reveal";
import { leafCategories, type PublicCategory } from "@/lib/catalog";

export async function CategoryStrip({
  locale,
  categories,
}: {
  locale: string;
  categories: PublicCategory[];
}) {
  const t = await getTranslations("storefront");
  const leaves = leafCategories(categories).slice(0, 8);

  return (
    <section className="mx-auto w-full max-w-6xl px-md py-3xl">
      <Reveal>
        <h2 className="font-display text-display text-ink">{t("categoriesTitle")}</h2>
        <p className="mt-sm max-w-lg text-muted">{t("categoriesLede")}</p>
      </Reveal>
      <ul className="mt-xl grid gap-sm sm:grid-cols-2 md:grid-cols-4">
        {leaves.map((cat, index) => (
          <li key={cat.id}>
            <Reveal delayMs={index * 60}>
              <Link
                href={`/${locale}/c/${cat.slug}`}
                className="block border-b border-line py-sm text-ink transition-colors hover:border-sage hover:text-sage-deep"
              >
                <span className="font-display text-xl">{cat.name}</span>
              </Link>
            </Reveal>
          </li>
        ))}
      </ul>
    </section>
  );
}

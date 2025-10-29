"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { AddToBagButton } from "@/components/storefront/AddToBagButton";
import { Reveal } from "@/components/motion/Reveal";
import { formatBdt, type PublicProduct } from "@/lib/catalog";
import { recordRecentlyViewed } from "@/lib/recently-viewed";

export function ProductDetail({
  product,
  locale,
}: {
  product: PublicProduct;
  locale: string;
}) {
  const t = useTranslations("storefront");
  const variants = useMemo(
    () => [...product.variants].sort((a, b) => a.sort_order - b.sort_order),
    [product.variants],
  );

  useEffect(() => {
    const prices = product.variants
      .filter((v) => v.is_active)
      .map((v) => v.price_poisha);
    recordRecentlyViewed({
      slug: product.slug,
      name: product.name,
      subtitle: product.subtitle,
      from_price_poisha: prices.length ? Math.min(...prices) : null,
    });
  }, [product]);
  const [variantId, setVariantId] = useState(variants[0]?.id ?? "");
  const selected = variants.find((v) => v.id === variantId) ?? variants[0];
  const productImage =
    product.images.find((i) => i.slot === "product") ?? product.images[0] ?? null;
  const textureImage = product.images.find((i) => i.slot === "texture") ?? null;
  const [showTexture, setShowTexture] = useState(false);
  const activeImage = showTexture && textureImage ? textureImage : productImage;
  const imageUrl =
    activeImage?.full_webp_url || activeImage?.card_webp_url || activeImage?.thumb_webp_url;

  const concerns = product.attributes.filter((a) => a.kind === "concern");
  const ingredients = product.attributes.filter((a) => a.kind === "ingredient");
  const skinTypes = product.attributes.filter((a) => a.kind === "skin_type");

  return (
    <article className="mx-auto w-full max-w-6xl px-md py-xl">
      <p className="text-sm text-muted">
        <Link href={`/${locale}/shop`} className="underline">
          {t("shop")}
        </Link>
        {product.category_slug ? (
          <>
            {" / "}
            <Link href={`/${locale}/c/${product.category_slug}`} className="underline">
              {product.category_slug}
            </Link>
          </>
        ) : null}
      </p>

      <div className="mt-lg grid gap-xl md:grid-cols-2">
        <Reveal>
          <div className="group relative aspect-[4/5] overflow-hidden bg-sage-soft/40">
            {imageUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={imageUrl}
                alt={activeImage?.alt_text || product.name}
                className="media-zoom h-full w-full object-cover"
              />
            ) : (
              <div className="flex h-full items-end bg-[radial-gradient(ellipse_at_50%_30%,#d8e4de,transparent_60%),linear-gradient(180deg,#e8eee9,#f2f4f1)] p-lg">
                <p className="font-display text-3xl text-sage-deep/70">{product.name}</p>
              </div>
            )}
            {textureImage ? (
              <button
                type="button"
                onClick={() => setShowTexture((v) => !v)}
                className="absolute bottom-md left-md rounded-sm bg-surface/90 px-sm py-xs text-xs text-ink backdrop-blur-sm"
              >
                {showTexture ? t("showProductShot") : t("showTexture")}
              </button>
            ) : null}
          </div>
        </Reveal>

        <div className="flex flex-col gap-lg">
          <Reveal>
            <h1 className="font-display text-hero text-ink">{product.name}</h1>
            {product.subtitle ? (
              <p className="mt-sm text-lg text-muted">{product.subtitle}</p>
            ) : null}
            <p className="mt-md text-xl font-medium text-ink">
              {formatBdt(selected?.price_poisha ?? null)}
            </p>
            {product.routine_step ? (
              <p className="mt-xs text-sm uppercase tracking-wide text-sage">
                {t("routineLabel", { step: product.routine_step })}
              </p>
            ) : null}
          </Reveal>

          {variants.length > 0 ? (
            <Reveal delayMs={80}>
              <fieldset>
                <legend className="mb-xs text-sm font-medium text-ink">{t("chooseSize")}</legend>
                <div className="flex flex-wrap gap-xs">
                  {variants.map((variant) => {
                    const label =
                      variant.size_label ||
                      variant.shade_name ||
                      (variant.spf != null ? `SPF ${variant.spf}` : variant.sku);
                    const active = variant.id === selected?.id;
                    return (
                      <button
                        key={variant.id}
                        type="button"
                        onClick={() => setVariantId(variant.id)}
                        className={
                          active
                            ? "rounded-sm bg-ink px-sm py-xs text-sm text-paper"
                            : "rounded-sm border border-line px-sm py-xs text-sm text-ink hover:border-sage"
                        }
                      >
                        {label}
                      </button>
                    );
                  })}
                </div>
              </fieldset>
            </Reveal>
          ) : null}

          <Reveal delayMs={120}>
            <AddToBagButton disabled={!selected} />
          </Reveal>

          {product.description ? (
            <Reveal delayMs={140}>
              <p className="text-base leading-relaxed text-ink">{product.description}</p>
            </Reveal>
          ) : null}

          {(skinTypes.length > 0 || concerns.length > 0 || ingredients.length > 0) ? (
            <Reveal delayMs={160}>
              <ul className="flex flex-wrap gap-xs text-xs text-muted">
                {skinTypes.map((a) => (
                  <li key={a.id} className="border-b border-line pb-2xs">
                    {a.name}
                  </li>
                ))}
                {concerns.map((a) => (
                  <li key={a.id} className="border-b border-line pb-2xs">
                    {a.name}
                  </li>
                ))}
                {ingredients.map((a) => (
                  <li key={a.id} className="border-b border-line pb-2xs">
                    {a.name}
                  </li>
                ))}
              </ul>
            </Reveal>
          ) : null}
        </div>
      </div>

      <div className="mt-3xl grid gap-xl md:grid-cols-3">
        <Reveal>
          <h2 className="font-display text-2xl text-ink">{t("howToUse")}</h2>
          <p className="mt-sm whitespace-pre-wrap text-sm leading-relaxed text-muted">
            {product.how_to_use || t("missingHowTo")}
          </p>
        </Reveal>
        <Reveal delayMs={80}>
          <h2 className="font-display text-2xl text-ink">{t("ingredients")}</h2>
          <p className="mt-sm whitespace-pre-wrap text-sm leading-relaxed text-muted">
            {product.ingredients_text || t("missingIngredients")}
          </p>
        </Reveal>
        <Reveal delayMs={140}>
          <h2 className="font-display text-2xl text-ink">{t("warnings")}</h2>
          <p className="mt-sm whitespace-pre-wrap text-sm leading-relaxed text-muted">
            {product.warnings || t("missingWarnings")}
          </p>
          {product.pao_months ? (
            <p className="mt-sm text-xs text-muted">
              {t("pao", { months: product.pao_months })}
            </p>
          ) : null}
        </Reveal>
      </div>
    </article>
  );
}

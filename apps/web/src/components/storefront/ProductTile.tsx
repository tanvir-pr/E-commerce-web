import Link from "next/link";
import { formatBdt, type PublicProductSummary } from "@/lib/catalog";

export function ProductTile({
  product,
  locale,
  index = 0,
}: {
  product: PublicProductSummary;
  locale: string;
  index?: number;
}) {
  return (
    <Link
      href={`/${locale}/p/${product.slug}`}
      className="group block border-b border-line py-md transition-colors hover:border-sage"
      style={{ transitionDelay: `${index * 40}ms` }}
    >
      <div className="flex items-baseline justify-between gap-md">
        <div>
          <p className="font-display text-xl text-ink">{product.name}</p>
          {product.subtitle ? (
            <p className="mt-2xs text-sm text-muted">{product.subtitle}</p>
          ) : null}
          <p className="mt-xs text-xs uppercase tracking-wide text-muted">
            {product.category_slug ?? "—"}
            {product.routine_step ? ` · ${product.routine_step}` : ""}
          </p>
        </div>
        <p className="shrink-0 text-sm font-medium text-ink">
          {formatBdt(product.from_price_poisha)}
        </p>
      </div>
    </Link>
  );
}

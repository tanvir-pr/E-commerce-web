import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

const LEGAL = [
  { key: "privacy", href: "/privacy" },
  { key: "terms", href: "/terms" },
  { key: "shipping", href: "/shipping" },
  { key: "returns", href: "/returns" },
] as const;

export async function SiteFooter() {
  const locale = await getLocale();
  const t = await getTranslations("footer");

  return (
    <footer className="mt-auto border-t border-line/80 bg-surface/60">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-md px-md py-lg md:flex-row md:items-start md:justify-between">
        <div>
          <p className="font-display text-lg text-ink">{t("brand")}</p>
          <p className="mt-2xs max-w-sm text-sm text-muted">{t("tagline")}</p>
        </div>
        <nav aria-label={t("legalNav")} className="flex flex-wrap gap-md text-sm">
          {LEGAL.map((item) => (
            <Link
              key={item.key}
              href={`/${locale}${item.href}`}
              className="text-muted underline-offset-2 hover:text-ink hover:underline"
            >
              {t(item.key)}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}

import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";
import { routing } from "@/i18n/routing";

export async function Header() {
  const t = await getTranslations("nav");
  const locale = await getLocale();
  return (
    <header className="sticky top-0 z-20 border-b border-line/80 bg-surface/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-md px-md py-sm">
        <Link
          href={`/${locale}`}
          className="font-display text-xl tracking-tight text-ink md:text-2xl"
        >
          {t("shopName")}
        </Link>
        <nav className="flex flex-wrap items-center justify-end gap-md text-sm">
          <Link href={`/${locale}/shop`} className="text-muted hover:text-ink">
            {t("shop")}
          </Link>
          <Link href={`/${locale}/search`} className="text-muted hover:text-ink">
            {t("search")}
          </Link>
          <Link href={`/${locale}/cart`} className="text-muted hover:text-ink">
            {t("cart")}
          </Link>
          <Link href={`/${locale}/orders`} className="text-muted hover:text-ink">
            {t("orders")}
          </Link>
          <Link href={`/${locale}/wishlist`} className="text-muted hover:text-ink">
            {t("wishlist")}
          </Link>
          <Link href={`/${locale}/account`} className="text-muted hover:text-ink">
            {t("account")}
          </Link>
          <Link href={`/${locale}/admin`} className="text-muted hover:text-ink">
            {t("admin")}
          </Link>
          <Link href={`/${locale}/login`} className="text-muted hover:text-ink">
            {t("login")}
          </Link>
          <Link href={`/${locale}/register`} className="text-muted hover:text-ink">
            {t("register")}
          </Link>
          <span className="flex gap-xs border-l border-line pl-md text-xs uppercase tracking-wide">
            {routing.locales.map((code) => (
              <Link
                key={code}
                href={`/${code}`}
                className={code === locale ? "text-ink" : "text-muted hover:text-ink"}
                hrefLang={code}
              >
                {code}
              </Link>
            ))}
          </span>
        </nav>
      </div>
    </header>
  );
}

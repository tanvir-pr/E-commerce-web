import { getLocale, getTranslations } from "next-intl/server";
import Link from "next/link";

export async function Header() {
  const t = await getTranslations("nav");
  const locale = await getLocale();
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-3xl items-center justify-between gap-md px-md py-sm">
        <Link href={`/${locale}`} className="text-lg font-semibold tracking-tight text-ink">
          {t("shopName")}
        </Link>
        <nav className="flex items-center gap-md text-sm">
          <Link href={`/${locale}/admin`} className="text-muted hover:text-ink">
            {t("admin")}
          </Link>
          <Link href={`/${locale}/login`} className="text-muted hover:text-ink">
            {t("login")}
          </Link>
          <Link href={`/${locale}/register`} className="text-muted hover:text-ink">
            {t("register")}
          </Link>
        </nav>
      </div>
    </header>
  );
}

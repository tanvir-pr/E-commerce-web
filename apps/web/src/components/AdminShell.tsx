import type { ReactNode } from "react";
import Link from "next/link";
import { getLocale, getTranslations } from "next-intl/server";

const NAV = [
  { key: "dashboard", href: "" },
  { key: "catalog", href: "/catalog" },
  { key: "carts", href: "/carts" },
  { key: "orders", href: "/orders" },
  { key: "courier", href: "/courier" },
  { key: "returns", href: "/returns" },
  { key: "customers", href: "/customers" },
  { key: "coupons", href: "/coupons" },
  { key: "reviews", href: "/reviews" },
  { key: "support", href: "/support" },
  { key: "settings", href: "/settings" },
] as const;

export async function AdminShell({
  children,
  title,
  active,
}: {
  children: ReactNode;
  title: string;
  active: (typeof NAV)[number]["key"];
}) {
  const locale = await getLocale();
  const t = await getTranslations("admin");
  const base = `/${locale}/admin`;

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-6xl flex-col gap-lg px-md py-lg md:flex-row">
      <aside className="w-full shrink-0 md:w-56">
        <p className="mb-sm text-xs font-semibold uppercase tracking-wide text-muted">
          {t("shellTitle")}
        </p>
        <nav className="flex flex-row flex-wrap gap-xs md:flex-col">
          {NAV.map((item) => {
            const href = `${base}${item.href}`;
            const isActive = item.key === active;
            return (
              <Link
                key={item.key}
                href={href}
                className={
                  isActive
                    ? "rounded-sm bg-ink px-sm py-xs text-sm text-paper"
                    : "rounded-sm px-sm py-xs text-sm text-muted hover:text-ink"
                }
              >
                {t(`nav.${item.key}`)}
              </Link>
            );
          })}
        </nav>
        <Link href={`/${locale}`} className="mt-md inline-block text-sm text-muted underline">
          {t("backStore")}
        </Link>
      </aside>
      <section className="min-w-0 flex-1">
        <h1 className="text-2xl font-semibold tracking-tight text-ink">{title}</h1>
        <div className="mt-md rounded-lg border border-line bg-surface p-lg">{children}</div>
      </section>
    </div>
  );
}

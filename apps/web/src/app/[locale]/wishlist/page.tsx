import { getTranslations, setRequestLocale } from "next-intl/server";
import { WishlistPanel } from "@/components/storefront/WishlistPanel";

export default async function WishlistPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("wishlist");
  return (
    <main className="mx-auto w-full max-w-3xl px-md py-xl">
      <h1 className="font-display text-hero text-ink">{t("pageTitle")}</h1>
      <p className="mt-sm text-muted">{t("lede")}</p>
      <div className="mt-xl">
        <WishlistPanel />
      </div>
    </main>
  );
}

import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { OrderDetailPanel } from "@/components/storefront/OrderDetailPanel";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "orders" });
  return pageMetadata({
    locale,
    path: "/orders",
    title: `${t("detailTitle")} · Solum`,
    description: t("lede"),
    noIndex: true,
  });
}

export default async function OrderDetailPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  return (
    <main id="main" className="mx-auto w-full max-w-6xl px-md py-xl">
      <OrderDetailPanel orderId={id} />
    </main>
  );
}

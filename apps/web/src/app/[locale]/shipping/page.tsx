import { getTranslations, setRequestLocale } from "next-intl/server";
import type { Metadata } from "next";
import { LegalPage } from "@/components/legal/LegalPage";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "legal" });
  return pageMetadata({
    locale,
    path: "/shipping",
    title: `${t("shipping.title")} · Solum`,
    description: t("shipping.metaDescription"),
  });
}

export default async function ShippingPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("legal");
  return (
    <LegalPage
      title={t("shipping.title")}
      updated={t("updated")}
      sections={[
        { heading: t("shipping.s1Title"), body: t("shipping.s1Body") },
        { heading: t("shipping.s2Title"), body: t("shipping.s2Body") },
        { heading: t("shipping.s3Title"), body: t("shipping.s3Body") },
      ]}
    />
  );
}

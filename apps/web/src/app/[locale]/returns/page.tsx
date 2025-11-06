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
    path: "/returns",
    title: `${t("returns.title")} · Solum`,
    description: t("returns.metaDescription"),
  });
}

export default async function ReturnsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("legal");
  return (
    <LegalPage
      title={t("returns.title")}
      updated={t("updated")}
      sections={[
        { heading: t("returns.s1Title"), body: t("returns.s1Body") },
        { heading: t("returns.s2Title"), body: t("returns.s2Body") },
        { heading: t("returns.s3Title"), body: t("returns.s3Body") },
      ]}
    />
  );
}

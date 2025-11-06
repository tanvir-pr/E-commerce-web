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
    path: "/privacy",
    title: `${t("privacy.title")} · Solum`,
    description: t("privacy.metaDescription"),
  });
}

export default async function PrivacyPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("legal");
  return (
    <LegalPage
      title={t("privacy.title")}
      updated={t("updated")}
      sections={[
        { heading: t("privacy.s1Title"), body: t("privacy.s1Body") },
        { heading: t("privacy.s2Title"), body: t("privacy.s2Body") },
        { heading: t("privacy.s3Title"), body: t("privacy.s3Body") },
      ]}
    />
  );
}

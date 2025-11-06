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
    path: "/terms",
    title: `${t("terms.title")} · Solum`,
    description: t("terms.metaDescription"),
  });
}

export default async function TermsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("legal");
  return (
    <LegalPage
      title={t("terms.title")}
      updated={t("updated")}
      sections={[
        { heading: t("terms.s1Title"), body: t("terms.s1Body") },
        { heading: t("terms.s2Title"), body: t("terms.s2Body") },
        { heading: t("terms.s3Title"), body: t("terms.s3Body") },
      ]}
    />
  );
}

import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminPlaceholder } from "@/components/AdminPlaceholder";
import { AdminShell } from "@/components/AdminShell";

export default async function AdminCatalogPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.catalog")} active="catalog">
      <AdminPlaceholder section={t("nav.catalog")} />
    </AdminShell>
  );
}

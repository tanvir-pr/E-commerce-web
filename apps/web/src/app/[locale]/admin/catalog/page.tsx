import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminShell } from "@/components/AdminShell";
import { CatalogAdmin } from "@/components/CatalogAdmin";

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
      <CatalogAdmin />
    </AdminShell>
  );
}

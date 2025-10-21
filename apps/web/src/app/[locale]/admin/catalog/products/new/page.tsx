import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminShell } from "@/components/AdminShell";
import { ProductEditor } from "@/components/ProductEditor";

export default async function AdminNewProductPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("adminCatalog");
  return (
    <AdminShell title={t("newProduct")} active="catalog">
      <ProductEditor />
    </AdminShell>
  );
}

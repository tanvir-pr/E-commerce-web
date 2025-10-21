import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminShell } from "@/components/AdminShell";
import { ProductEditor } from "@/components/ProductEditor";

export default async function AdminEditProductPage({
  params,
}: {
  params: Promise<{ locale: string; id: string }>;
}) {
  const { locale, id } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("adminCatalog");
  return (
    <AdminShell title={t("editProduct")} active="catalog">
      <ProductEditor productId={id} />
    </AdminShell>
  );
}

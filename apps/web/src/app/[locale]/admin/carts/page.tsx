import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminPlaceholder } from "@/components/AdminPlaceholder";
import { AdminShell } from "@/components/AdminShell";

export default async function AdminCartsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.carts")} active="carts">
      <AdminPlaceholder section={t("nav.carts")} />
    </AdminShell>
  );
}

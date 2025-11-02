import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminCarts } from "@/components/AdminCarts";
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
      <AdminCarts />
    </AdminShell>
  );
}

import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminOrders } from "@/components/AdminOrders";
import { AdminShell } from "@/components/AdminShell";

export default async function AdminOrdersPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.orders")} active="orders">
      <AdminOrders />
    </AdminShell>
  );
}

import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminCoupons } from "@/components/AdminCoupons";
import { AdminShell } from "@/components/AdminShell";

export default async function AdminCouponsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.coupons")} active="coupons">
      <AdminCoupons />
    </AdminShell>
  );
}

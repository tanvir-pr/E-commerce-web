import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminReturns } from "@/components/AdminReturns";
import { AdminShell } from "@/components/AdminShell";

export default async function AdminReturnsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.returns")} active="returns">
      <AdminReturns />
    </AdminShell>
  );
}

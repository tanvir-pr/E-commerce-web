import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminShell } from "@/components/AdminShell";
import { AdminSupport } from "@/components/AdminSupport";

export default async function AdminSupportPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.support")} active="support">
      <AdminSupport />
    </AdminShell>
  );
}

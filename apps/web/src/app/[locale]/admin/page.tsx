import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminDashboard } from "@/components/AdminDashboard";
import { AdminShell } from "@/components/AdminShell";

export default async function AdminHomePage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.dashboard")} active="dashboard">
      <AdminDashboard />
    </AdminShell>
  );
}

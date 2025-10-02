import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminShell } from "@/components/AdminShell";
import { StaffCreateForm } from "@/components/StaffCreateForm";

export default async function AdminSettingsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.settings")} active="settings">
      <StaffCreateForm />
    </AdminShell>
  );
}

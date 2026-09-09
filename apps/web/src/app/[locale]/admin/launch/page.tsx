import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminLaunchChecklist } from "@/components/AdminLaunchChecklist";
import { AdminShell } from "@/components/AdminShell";

export default async function AdminLaunchPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.launch")} active="launch">
      <AdminLaunchChecklist />
    </AdminShell>
  );
}

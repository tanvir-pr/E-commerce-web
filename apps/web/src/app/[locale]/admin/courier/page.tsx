import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminCourierBoard } from "@/components/AdminCourierBoard";
import { AdminShell } from "@/components/AdminShell";

export default async function AdminCourierPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.courier")} active="courier">
      <AdminCourierBoard />
    </AdminShell>
  );
}

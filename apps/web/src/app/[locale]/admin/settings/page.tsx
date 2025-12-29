import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminFeatureFlags } from "@/components/AdminFeatureFlags";
import { AdminShippingZones } from "@/components/AdminShippingZones";
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
      <div className="flex flex-col gap-xl">
        <section>
          <h2 className="mb-md text-sm font-semibold text-ink">{t("settingsFlags")}</h2>
          <AdminFeatureFlags />
        </section>
        <section>
          <h2 className="mb-md text-sm font-semibold text-ink">{t("settingsStaff")}</h2>
          <StaffCreateForm />
        </section>
        <section>
          <h2 className="mb-md text-sm font-semibold text-ink">{t("settingsShipping")}</h2>
          <AdminShippingZones />
        </section>
      </div>
    </AdminShell>
  );
}

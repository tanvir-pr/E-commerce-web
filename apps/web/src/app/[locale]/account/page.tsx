import { getTranslations, setRequestLocale } from "next-intl/server";
import { AccountPanel } from "@/components/AccountPanel";
import { PageShell } from "@/components/PageShell";

export default async function AccountPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("account");

  return (
    <PageShell title={t("title")} lede={t("lede")} wide>
      <AccountPanel />
    </PageShell>
  );
}

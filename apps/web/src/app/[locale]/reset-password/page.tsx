import { getTranslations, setRequestLocale } from "next-intl/server";
import { ResetPasswordForm } from "@/components/ResetPasswordForm";
import { PageShell } from "@/components/PageShell";

export default async function ResetPasswordPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ token?: string }>;
}) {
  const { locale } = await params;
  const query = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations("account");

  return (
    <PageShell title={t("resetTitle")} lede={t("resetHint")}>
      <ResetPasswordForm token={query.token ?? null} />
    </PageShell>
  );
}

import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";
import { ForgotPasswordForm } from "@/components/ForgotPasswordForm";
import { PageShell } from "@/components/PageShell";

export default async function ForgotPasswordPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("account");

  return (
    <PageShell title={t("forgotTitle")} lede={t("forgotHint")}>
      <ForgotPasswordForm />
      <p className="mt-lg text-sm text-muted">
        <Link href={`/${locale}/login`} className="underline">
          {t("backToLogin")}
        </Link>
      </p>
    </PageShell>
  );
}

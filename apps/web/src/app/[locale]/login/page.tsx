import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";
import { LoginForm } from "@/components/LoginForm";
import { PageShell } from "@/components/PageShell";

export default async function LoginPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("auth");

  return (
    <PageShell title={t("loginTitle")} lede={t("loginHint")}>
      <LoginForm />
      <p className="mt-lg text-sm text-muted">
        <Link href={`/${locale}/forgot-password`} className="underline">
          {t("forgotPassword")}
        </Link>
      </p>
      <p className="mt-sm text-sm text-muted">
        <Link href={`/${locale}/register`} className="underline">
          {t("needAccount")}
        </Link>
      </p>
    </PageShell>
  );
}

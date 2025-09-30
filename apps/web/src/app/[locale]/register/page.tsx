import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";
import { PageShell } from "@/components/PageShell";
import { RegisterForm } from "@/components/RegisterForm";

export default async function RegisterPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("auth");

  return (
    <PageShell title={t("registerTitle")} lede={t("registerHint")}>
      <RegisterForm />
      <p className="mt-lg text-sm text-muted">
        <Link href={`/${locale}/login`} className="underline">
          {t("haveAccount")}
        </Link>
      </p>
    </PageShell>
  );
}

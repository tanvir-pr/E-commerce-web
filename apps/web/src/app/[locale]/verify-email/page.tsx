import { getTranslations, setRequestLocale } from "next-intl/server";
import Link from "next/link";
import { PageShell } from "@/components/PageShell";
import { VerifyEmail } from "@/components/VerifyEmail";

export default async function VerifyEmailPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ token?: string }>;
}) {
  const { locale } = await params;
  const query = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations("auth");

  return (
    <PageShell title={t("verifyTitle")}>
      <VerifyEmail token={query.token ?? null} />
      <p className="mt-lg text-sm text-muted">
        <Link href={`/${locale}/login`} className="underline">
          {t("goLogin")}
        </Link>
      </p>
    </PageShell>
  );
}

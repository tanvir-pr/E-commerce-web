import type { Metadata } from "next";
import { getTranslations, setRequestLocale } from "next-intl/server";
import { SandboxPayPanel } from "@/components/storefront/SandboxPayPanel";
import { pageMetadata } from "@/lib/seo";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ locale: string }>;
}): Promise<Metadata> {
  const { locale } = await params;
  const t = await getTranslations({ locale, namespace: "paySandbox" });
  return pageMetadata({
    locale,
    path: "/pay/sandbox",
    title: `${t("title")} · Solum`,
    description: t("lede"),
    noIndex: true,
  });
}

export default async function PaySandboxPage({
  params,
  searchParams,
}: {
  params: Promise<{ locale: string }>;
  searchParams: Promise<{ method?: string; token?: string; return?: string }>;
}) {
  const { locale } = await params;
  const query = await searchParams;
  setRequestLocale(locale);
  return (
    <main id="main" className="mx-auto w-full max-w-lg px-md py-xl">
      <SandboxPayPanel
        method={query.method ?? "bkash"}
        token={query.token ?? ""}
        returnPath={query.return ?? `/${locale}/orders`}
      />
    </main>
  );
}

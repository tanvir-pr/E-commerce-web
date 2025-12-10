import { getTranslations, setRequestLocale } from "next-intl/server";
import { AdminReviews } from "@/components/AdminReviews";
import { AdminShell } from "@/components/AdminShell";

export default async function AdminReviewsPage({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  setRequestLocale(locale);
  const t = await getTranslations("admin");
  return (
    <AdminShell title={t("nav.reviews")} active="reviews">
      <AdminReviews />
    </AdminShell>
  );
}

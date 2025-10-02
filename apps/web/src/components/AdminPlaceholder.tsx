"use client";

import { useTranslations } from "next-intl";

export function AdminPlaceholder({ section }: { section: string }) {
  const t = useTranslations("admin");
  return <p className="text-sm text-muted">{t("comingSoon", { section })}</p>;
}

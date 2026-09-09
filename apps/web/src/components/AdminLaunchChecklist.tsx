"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { fetchMe, isStaff, type Me } from "@/lib/api";
import { fetchLaunchReadiness, type LaunchReadiness } from "@/lib/launch";

export function AdminLaunchChecklist() {
  const t = useTranslations("adminLaunch");
  const ta = useTranslations("admin");
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [report, setReport] = useState<LaunchReadiness | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const current = await fetchMe();
      if (!active) {
        return;
      }
      setMe(current);
      if (!isStaff(current)) {
        setError(ta("forbidden"));
        return;
      }
      try {
        setReport(await fetchLaunchReadiness());
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : t("loadFailed"));
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [t, ta]);

  if (me === undefined) {
    return <p className="text-sm text-muted">{ta("loading")}</p>;
  }
  if (error) {
    return (
      <p role="alert" className="text-sm text-danger">
        {error}
      </p>
    );
  }
  if (!report) {
    return <p className="text-sm text-muted">{ta("loading")}</p>;
  }

  return (
    <div className="flex flex-col gap-lg">
      <p className="text-sm text-muted">{t("hint")}</p>
      <div className="grid gap-sm sm:grid-cols-3">
        <div className="border border-line p-sm">
          <p className="text-xs text-muted">{t("ready")}</p>
          <p className="mt-2xs text-lg font-semibold text-ink">
            {report.ready_for_launch ? t("yes") : t("no")}
          </p>
        </div>
        <div className="border border-line p-sm">
          <p className="text-xs text-muted">{t("blocking")}</p>
          <p className="mt-2xs text-lg font-semibold text-ink">{report.blocking_failures}</p>
        </div>
        <div className="border border-line p-sm">
          <p className="text-xs text-muted">{t("manual")}</p>
          <p className="mt-2xs text-lg font-semibold text-ink">{report.manual_items}</p>
        </div>
      </div>
      <p className="text-xs text-muted">
        {t("alembic", { version: report.expected_alembic })}
      </p>
      <ul className="divide-y divide-line border-t border-line">
        {report.checks.map((check) => (
          <li key={check.key} className="flex flex-wrap items-start justify-between gap-md py-md">
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium text-ink">{check.title}</p>
              <p className="mt-2xs text-sm text-muted">{check.detail}</p>
            </div>
            <span
              className={
                check.status === "pass"
                  ? "text-sm text-ok"
                  : check.status === "fail"
                    ? "text-sm text-danger"
                    : "text-sm text-muted"
              }
            >
              {t(`status.${check.status}` as "status.pass")}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

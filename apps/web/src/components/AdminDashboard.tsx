"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { fetchMe, isStaff, type Me } from "@/lib/api";

type AuditItem = {
  id: string;
  action: string;
  actor_user_id: string | null;
  subject_type: string | null;
  subject_id: string | null;
  created_at: string;
};

export function AdminDashboard() {
  const t = useTranslations("admin");
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [audit, setAudit] = useState<AuditItem[]>([]);
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
        setError(t("forbidden"));
        return;
      }
      const response = await fetch("/api/v1/admin/audit", {
        credentials: "include",
        cache: "no-store",
      });
      if (!response.ok) {
        setError(t("auditFailed"));
        return;
      }
      const body = (await response.json()) as { items: AuditItem[] };
      setAudit(body.items);
    })();
    return () => {
      active = false;
    };
  }, [t]);

  if (me === undefined) {
    return <p className="text-sm text-muted">{t("loading")}</p>;
  }
  if (error) {
    return (
      <p role="alert" className="text-sm text-danger">
        {error}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-lg">
      <p className="text-sm text-ink">
        {t("signedIn", { email: me?.email ?? "" })}
        {me?.totp_enabled ? ` · ${t("totpOn")}` : ""}
      </p>
      <div>
        <h2 className="text-sm font-semibold text-ink">{t("recentAudit")}</h2>
        {audit.length === 0 ? (
          <p className="mt-sm text-sm text-muted">{t("noAudit")}</p>
        ) : (
          <ul className="mt-sm divide-y divide-line border border-line">
            {audit.map((item) => (
              <li key={item.id} className="flex flex-col gap-xs px-sm py-sm text-sm md:flex-row md:justify-between">
                <span className="font-mono text-ink">{item.action}</span>
                <span className="text-muted">{new Date(item.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

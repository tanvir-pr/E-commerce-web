"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { apiPost, fetchCsrfToken, fetchHealth, fetchMe, type Me } from "@/lib/api";

export function HomePanel() {
  const t = useTranslations("home");
  const locale = useLocale();
  const router = useRouter();
  const [health, setHealth] = useState<"checking" | "ok" | "down">("checking");
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      const [healthResult, meResult] = await Promise.all([fetchHealth(), fetchMe()]);
      if (!active) {
        return;
      }
      setHealth(healthResult ? "ok" : "down");
      setMe(meResult);
    })();
    return () => {
      active = false;
    };
  }, []);

  async function onLogout() {
    setSigningOut(true);
    try {
      const csrf = await fetchCsrfToken();
      await apiPost("/api/v1/auth/logout", {}, csrf);
      setMe(null);
      router.refresh();
    } finally {
      setSigningOut(false);
    }
  }

  const healthText =
    health === "checking" ? t("healthChecking") : health === "ok" ? t("healthOk") : t("healthDown");
  const healthClass =
    health === "down"
      ? "text-base font-medium text-danger"
      : health === "ok"
        ? "text-base font-medium text-ok"
        : "text-base font-medium text-muted";

  return (
    <div className="flex flex-col gap-md">
      <p role="status" className={healthClass}>
        {healthText}
      </p>
      {me === undefined ? (
        <p className="text-sm text-muted">{t("sessionChecking")}</p>
      ) : me ? (
        <div className="flex flex-col gap-sm">
          <p className="text-sm text-ink">
            {t("signedInAs", { email: me.email })}
            {me.email_verified_at ? ` · ${t("verified")}` : ` · ${t("notVerified")}`}
          </p>
          <button
            type="button"
            onClick={() => void onLogout()}
            disabled={signingOut}
            className="w-fit rounded-sm border border-line px-md py-sm text-sm text-ink disabled:opacity-60"
          >
            {signingOut ? t("signingOut") : t("signOut")}
          </button>
        </div>
      ) : (
        <p className="text-sm text-muted">
          <a href={`/${locale}/login`} className="underline">
            {t("signInLink")}
          </a>
        </p>
      )}
    </div>
  );
}

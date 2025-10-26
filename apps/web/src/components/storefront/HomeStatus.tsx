"use client";

import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { apiPost, fetchCsrfToken, fetchHealth, fetchMe, type Me } from "@/lib/api";

/** Dev/session strip — kept below the first viewport on purpose. */
export function HomeStatus() {
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

  return (
    <section className="border-t border-line bg-surface/80">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-sm px-md py-lg text-sm">
        <p
          role="status"
          className={
            health === "down" ? "text-danger" : health === "ok" ? "text-ok" : "text-muted"
          }
        >
          {healthText}
        </p>
        {me === undefined ? (
          <p className="text-muted">{t("sessionChecking")}</p>
        ) : me ? (
          <div className="flex flex-wrap items-center gap-sm">
            <p className="text-ink">
              {t("signedInAs", { email: me.email })}
              {me.email_verified_at ? ` · ${t("verified")}` : ` · ${t("notVerified")}`}
            </p>
            <a href={`/${locale}/account`} className="underline">
              {t("accountLink")}
            </a>
            <button
              type="button"
              onClick={() => void onLogout()}
              disabled={signingOut}
              className="underline disabled:opacity-60"
            >
              {signingOut ? t("signingOut") : t("signOut")}
            </button>
          </div>
        ) : (
          <a href={`/${locale}/login`} className="w-fit underline">
            {t("signInLink")}
          </a>
        )}
      </div>
    </section>
  );
}

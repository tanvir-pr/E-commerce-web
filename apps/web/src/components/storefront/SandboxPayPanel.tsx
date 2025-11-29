"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Reveal } from "@/components/motion/Reveal";

export function SandboxPayPanel({
  method,
  token,
  returnPath,
}: {
  method: string;
  token: string;
  returnPath: string;
}) {
  const t = useTranslations("paySandbox");
  const tOrders = useTranslations("orders");
  const locale = useLocale();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  const gatewayLabel =
    method === "sslcommerz"
      ? tOrders("paymentMethod.sslcommerz")
      : tOrders("paymentMethod.bkash");

  function complete(success: boolean) {
    if (!token) {
      setError(t("missingToken"));
      return;
    }
    if (!success) {
      router.push(returnPath || `/${locale}/orders`);
      return;
    }
    // Session-less API return → 303 to order (no CSRF / login cookie required).
    const status = method === "sslcommerz" ? "VALID" : "Completed";
    const params = new URLSearchParams({
      token,
      status,
      locale,
    });
    window.location.assign(`/api/v1/payments/${encodeURIComponent(method)}/return?${params}`);
  }

  return (
    <Reveal>
      <p className="text-sm text-muted">{t("sandboxBadge")}</p>
      <h1 className="mt-sm font-display text-display text-ink">{t("title")}</h1>
      <p className="mt-sm text-muted">{t("lede", { gateway: gatewayLabel })}</p>
      {!token ? (
        <p role="alert" className="mt-md text-sm text-danger">
          {t("missingToken")}
        </p>
      ) : null}
      {error ? (
        <p role="alert" className="mt-md text-sm text-danger">
          {error}
        </p>
      ) : null}
      <div className="mt-xl flex flex-wrap gap-sm">
        <button
          type="button"
          disabled={!token}
          onClick={() => complete(true)}
          className="rounded-sm bg-sage px-md py-sm text-sm font-medium text-white hover:bg-sage-deep disabled:opacity-60"
        >
          {t("paySuccess")}
        </button>
        <button
          type="button"
          onClick={() => complete(false)}
          className="rounded-sm border border-line px-md py-sm text-sm text-ink"
        >
          {t("payFail")}
        </button>
      </div>
      <p className="mt-md text-sm text-muted">
        <Link href={returnPath || `/${locale}/orders`} className="underline">
          {t("back")}
        </Link>
      </p>
    </Reveal>
  );
}

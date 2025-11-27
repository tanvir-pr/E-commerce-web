"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { Reveal } from "@/components/motion/Reveal";
import { validatePayment } from "@/lib/orders";

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
  const [pending, setPending] = useState(false);

  const gatewayLabel =
    method === "sslcommerz"
      ? tOrders("paymentMethod.sslcommerz")
      : tOrders("paymentMethod.bkash");

  async function complete(success: boolean) {
    if (!token) {
      setError(t("missingToken"));
      return;
    }
    if (!success) {
      router.push(returnPath || `/${locale}/orders`);
      return;
    }
    setPending(true);
    setError(null);
    try {
      const status = method === "sslcommerz" ? "VALID" : "Completed";
      const out = await validatePayment(method, { token, status });
      router.push(`/${locale}/orders/${out.order_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("failed"));
      setPending(false);
    }
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
          disabled={pending || !token}
          onClick={() => void complete(true)}
          className="rounded-sm bg-sage px-md py-sm text-sm font-medium text-white hover:bg-sage-deep disabled:opacity-60"
        >
          {pending ? t("working") : t("paySuccess")}
        </button>
        <button
          type="button"
          disabled={pending}
          onClick={() => void complete(false)}
          className="rounded-sm border border-line px-md py-sm text-sm text-ink disabled:opacity-60"
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

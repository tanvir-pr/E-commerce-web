"use client";

import { useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { addToCart } from "@/lib/cart";

export function AddToBagButton({
  variantId,
  disabled,
}: {
  variantId?: string;
  disabled?: boolean;
}) {
  const t = useTranslations("cart");
  const locale = useLocale();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [added, setAdded] = useState(false);
  const [pop, setPop] = useState(false);

  async function onClick() {
    if (!variantId) {
      return;
    }
    setPending(true);
    setError(null);
    setPop(true);
    window.setTimeout(() => setPop(false), 320);
    try {
      await addToCart(variantId, 1);
      setAdded(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("addFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-xs">
      <button
        type="button"
        disabled={disabled || !variantId || pending}
        onClick={() => void onClick()}
        className={`btn-press rounded-sm bg-saffron px-lg py-sm text-sm font-medium text-ink disabled:opacity-50 ${
          pop ? "animate-press-pop" : ""
        }`}
      >
        {pending ? t("adding") : t("addToBag")}
      </button>
      {error ? (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      ) : null}
      {added ? (
        <p role="status" className="text-xs text-ok">
          {t("added")}{" "}
          <Link href={`/${locale}/cart`} className="underline">
            {t("viewCart")}
          </Link>
        </p>
      ) : null}
    </div>
  );
}

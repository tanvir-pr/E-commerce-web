"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Reveal } from "@/components/motion/Reveal";
import { formatBdt } from "@/lib/catalog";
import {
  clearCart,
  fetchCart,
  fetchUpsell,
  patchCartItem,
  removeCartItem,
  type Cart,
  type Upsell,
} from "@/lib/cart";

export function CartPanel() {
  const t = useTranslations("cart");
  const locale = useLocale();
  const [cart, setCart] = useState<Cart | null>(null);
  const [upsell, setUpsell] = useState<Upsell | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [nextCart, nextUpsell] = await Promise.all([fetchCart(), fetchUpsell()]);
      setCart(nextCart);
      setUpsell(nextUpsell);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loadFailed"));
    }
  }, [t]);

  useEffect(() => {
    void load();
  }, [load]);

  async function onQty(itemId: string, qty: number) {
    setPending(true);
    setError(null);
    try {
      const next = qty <= 0 ? await removeCartItem(itemId) : await patchCartItem(itemId, qty);
      setCart(next);
      setUpsell(await fetchUpsell());
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onClear() {
    if (!window.confirm(t("clearConfirm"))) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      setCart(await clearCart());
      setUpsell(await fetchUpsell());
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  if (!cart && !error) {
    return <p className="text-sm text-muted">{t("loading")}</p>;
  }

  return (
    <div className="flex flex-col gap-xl">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      {!cart || cart.items.length === 0 ? (
        <Reveal>
          <p className="text-muted">{t("empty")}</p>
          <Link href={`/${locale}/shop`} className="mt-md inline-block text-sage underline">
            {t("continueShopping")}
          </Link>
        </Reveal>
      ) : (
        <>
          <Reveal>
            <ul className="divide-y divide-line border-t border-line">
              {cart.items.map((item) => (
                <li
                  key={item.id}
                  className="flex flex-col gap-sm py-md md:flex-row md:items-center md:justify-between"
                >
                  <div>
                    <Link
                      href={`/${locale}/p/${item.product_slug}`}
                      className="font-display text-xl text-ink underline-offset-2 hover:underline"
                    >
                      {item.product_name}
                    </Link>
                    <p className="mt-2xs text-sm text-muted">
                      {[item.size_label, item.shade_name, item.spf != null ? `SPF ${item.spf}` : null]
                        .filter(Boolean)
                        .join(" · ") || item.sku}
                    </p>
                    <p className="mt-2xs text-sm text-ink">
                      {formatBdt(item.unit_price_poisha)} × {item.qty}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-sm">
                    <label className="flex items-center gap-xs text-sm">
                      <span className="text-muted">{t("qty")}</span>
                      <input
                        type="number"
                        min={0}
                        max={20}
                        value={item.qty}
                        disabled={pending}
                        onChange={(e) =>
                          void onQty(item.id, Number.parseInt(e.target.value, 10) || 0)
                        }
                        className="w-16 rounded-sm border border-line bg-surface px-sm py-xs text-ink"
                      />
                    </label>
                    <p className="text-sm font-medium text-ink">
                      {formatBdt(item.line_total_poisha)}
                    </p>
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => void onQty(item.id, 0)}
                      className="text-sm text-danger underline disabled:opacity-60"
                    >
                      {t("remove")}
                    </button>
                  </div>
                </li>
              ))}
            </ul>
            <div className="mt-lg flex flex-wrap items-center justify-between gap-md border-t border-line pt-md">
              <p className="text-lg font-medium text-ink">
                {t("subtotal")} · {formatBdt(cart.subtotal_poisha)}
              </p>
              <div className="flex flex-wrap gap-sm">
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => void onClear()}
                  className="rounded-sm border border-line px-md py-sm text-sm disabled:opacity-60"
                >
                  {t("clear")}
                </button>
                <Link
                  href={`/${locale}/shop`}
                  className="rounded-sm border border-line px-md py-sm text-sm"
                >
                  {t("continueShopping")}
                </Link>
                <span className="rounded-sm bg-sage px-md py-sm text-sm font-medium text-white opacity-70">
                  {t("checkoutSoon")}
                </span>
              </div>
            </div>
          </Reveal>

          {upsell && upsell.items.length > 0 ? (
            <Reveal>
              <h2 className="font-display text-display text-ink">{t("upsellTitle")}</h2>
              <p className="mt-sm max-w-xl text-muted">{t("upsellLede")}</p>
              <ul className="mt-md divide-y divide-line border-t border-line">
                {upsell.items.map((item) => (
                  <li key={item.product_id} className="flex flex-wrap items-baseline justify-between gap-md py-md">
                    <div>
                      <Link
                        href={`/${locale}/p/${item.slug}`}
                        className="font-display text-xl text-ink hover:text-sage-deep"
                      >
                        {item.name}
                      </Link>
                      <p className="text-sm text-muted">{item.reason}</p>
                    </div>
                    <p className="text-sm font-medium text-ink">
                      {formatBdt(item.from_price_poisha)}
                    </p>
                  </li>
                ))}
              </ul>
            </Reveal>
          ) : null}
        </>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Reveal } from "@/components/motion/Reveal";
import { fetchMe, type Me } from "@/lib/api";
import { formatBdt } from "@/lib/catalog";
import { fetchMyOrders, type OrderSummary } from "@/lib/orders";

export function OrdersPanel() {
  const t = useTranslations("orders");
  const locale = useLocale();
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [items, setItems] = useState<OrderSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const current = await fetchMe();
      if (!active) {
        return;
      }
      setMe(current);
      if (!current) {
        return;
      }
      try {
        setItems(await fetchMyOrders());
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : t("loadFailed"));
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [t]);

  if (me === undefined) {
    return <p className="text-sm text-muted">{t("loading")}</p>;
  }
  if (!me) {
    return (
      <Reveal>
        <p className="text-muted">{t("signInRequired")}</p>
        <Link href={`/${locale}/login`} className="mt-md inline-block text-sage underline">
          {t("signIn")}
        </Link>
      </Reveal>
    );
  }

  return (
    <div className="flex flex-col gap-md">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {items.length === 0 ? (
        <p className="text-sm text-muted">{t("empty")}</p>
      ) : (
        <ul className="divide-y divide-line border-t border-line">
          {items.map((row) => (
            <li key={row.id} className="flex flex-wrap items-center justify-between gap-sm py-md text-sm">
              <div>
                <Link
                  href={`/${locale}/orders/${row.id}`}
                  className="font-medium text-ink underline-offset-2 hover:underline"
                >
                  {row.order_number}
                </Link>
                <p className="text-xs text-muted">
                  {t(`status.${row.status}`)} · {new Date(row.placed_at).toLocaleString()}
                </p>
              </div>
              <p className="font-medium text-ink">{formatBdt(row.total_poisha)}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

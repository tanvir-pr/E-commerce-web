"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Reveal } from "@/components/motion/Reveal";
import { fetchMe, type Me } from "@/lib/api";
import { formatBdt } from "@/lib/catalog";
import { cancelMyOrder, fetchMyOrder, type Order } from "@/lib/orders";

export function OrderDetailPanel({ orderId }: { orderId: string }) {
  const t = useTranslations("orders");
  const locale = useLocale();
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setOrder(await fetchMyOrder(orderId));
  }, [orderId]);

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
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : t("loadFailed"));
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load, t]);

  async function onCancel() {
    if (!window.confirm(t("cancelConfirm"))) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      setOrder(await cancelMyOrder(orderId));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("cancelFailed"));
    } finally {
      setPending(false);
    }
  }

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
  if (!order && !error) {
    return <p className="text-sm text-muted">{t("loading")}</p>;
  }
  if (!order) {
    return (
      <p role="alert" className="text-sm text-danger">
        {error}
      </p>
    );
  }

  const addr = order.shipping_address;

  return (
    <div className="flex flex-col gap-xl">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      <Reveal>
        <p className="text-sm text-muted">
          <Link href={`/${locale}/orders`} className="underline">
            {t("backList")}
          </Link>
        </p>
        <h2 className="mt-md font-display text-display text-ink">{order.order_number}</h2>
        <p className="mt-sm text-muted">
          {t(`status.${order.status}`)} · {new Date(order.placed_at).toLocaleString()}
        </p>
        {order.reservation_expires_at && order.status === "pending_payment" ? (
          <p className="mt-2xs text-sm text-muted">
            {t("reservationHold", {
              when: new Date(order.reservation_expires_at).toLocaleString(),
            })}
          </p>
        ) : null}
        {order.allowed_transitions.includes("cancelled") ? (
          <p className="mt-2xs text-sm text-muted">{t("cancelHint")}</p>
        ) : null}
      </Reveal>

      <Reveal>
        <h3 className="text-sm font-semibold text-ink">{t("paymentTitle")}</h3>
        <p className="mt-sm text-sm text-muted">
          {order.payment_method
            ? t(`paymentMethod.${order.payment_method}` as "paymentMethod.cod")
            : "—"}
          {order.payment_status
            ? ` · ${t(`paymentStatus.${order.payment_status}` as "paymentStatus.pending")}`
            : ""}
        </p>
        {order.courier_name || order.tracking_number ? (
          <p className="mt-2xs text-sm text-muted">
            {t("trackingLine", {
              courier: order.courier_name ?? "—",
              tracking: order.tracking_number ?? "—",
            })}
          </p>
        ) : null}
      </Reveal>

      <Reveal>
        <h3 className="text-sm font-semibold text-ink">{t("itemsTitle")}</h3>
        <ul className="mt-sm divide-y divide-line border-t border-line text-sm">
          {order.items.map((item) => (
            <li key={item.id} className="flex justify-between gap-md py-sm">
              <span>
                {item.product_name} × {item.qty}
              </span>
              <span>{formatBdt(item.line_total_poisha)}</span>
            </li>
          ))}
        </ul>
        <div className="mt-md flex flex-col gap-2xs border-t border-line pt-md text-sm">
          <p className="flex justify-between">
            <span className="text-muted">{t("merchandise")}</span>
            <span>{formatBdt(order.merchandise_subtotal_poisha)}</span>
          </p>
          <p className="flex justify-between">
            <span className="text-muted">{t("shipping")}</span>
            <span>{formatBdt(order.shipping_poisha)}</span>
          </p>
          <p className="flex justify-between font-medium text-ink">
            <span>{t("total")}</span>
            <span>{formatBdt(order.total_poisha)}</span>
          </p>
        </div>
      </Reveal>

      <Reveal>
        <h3 className="text-sm font-semibold text-ink">{t("addressTitle")}</h3>
        <p className="mt-sm text-sm text-muted">
          {addr.line1}
          {addr.city ? `, ${addr.city}` : ""}
          {addr.district ? `, ${addr.district}` : ""}
        </p>
      </Reveal>

      <Reveal>
        <h3 className="text-sm font-semibold text-ink">{t("timelineTitle")}</h3>
        <ol className="mt-sm divide-y divide-line border-t border-line text-sm">
          {order.events.map((event) => (
            <li key={event.id} className="py-sm">
              <p className="font-medium text-ink">
                {event.from_status
                  ? `${t(`status.${event.from_status}`)} → ${t(`status.${event.to_status}`)}`
                  : t(`status.${event.to_status}`)}
              </p>
              <p className="text-xs text-muted">
                {new Date(event.created_at).toLocaleString()}
                {event.note ? ` · ${event.note}` : ""}
              </p>
            </li>
          ))}
        </ol>
      </Reveal>

      {order.allowed_transitions.includes("cancelled") ? (
        <button
          type="button"
          disabled={pending}
          onClick={() => void onCancel()}
          className="w-fit rounded-sm border border-danger px-md py-sm text-sm text-danger disabled:opacity-60"
        >
          {pending ? t("cancelling") : t("cancel")}
        </button>
      ) : null}
    </div>
  );
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Reveal } from "@/components/motion/Reveal";
import { fetchMe, type Me } from "@/lib/api";
import { formatBdt } from "@/lib/catalog";
import {
  cancelMyOrder,
  createReturnRequest,
  fetchMyOrder,
  startOrderPayment,
  type Order,
} from "@/lib/orders";

type TrackStep = {
  key: string;
  at: string | null;
  state: "done" | "current" | "upcoming";
};

function buildTrackSteps(order: Order): TrackStep[] {
  const happy = ["pending_payment", "confirmed", "shipped", "delivered"] as const;
  const stamps: Record<string, string | null> = {
    pending_payment: order.placed_at,
    confirmed: order.confirmed_at,
    shipped: order.shipped_at,
    delivered: order.delivered_at,
  };

  if (order.status === "cancelled") {
    const steps: TrackStep[] = [];
    for (const key of happy) {
      const at = stamps[key];
      if (!at) {
        break;
      }
      steps.push({ key, at, state: "done" });
    }
    steps.push({ key: "cancelled", at: order.cancelled_at, state: "current" });
    return steps;
  }

  if (order.status === "returned") {
    const steps: TrackStep[] = [
      { key: "pending_payment", at: order.placed_at, state: "done" },
      { key: "confirmed", at: order.confirmed_at, state: "done" },
      { key: "shipped", at: order.shipped_at, state: "done" },
    ];
    if (order.delivery_failed_at) {
      steps.push({ key: "delivery_failed", at: order.delivery_failed_at, state: "done" });
    }
    steps.push({ key: "returned", at: order.returned_at, state: "current" });
    return steps;
  }

  if (order.status === "delivery_failed") {
    return [
      { key: "pending_payment", at: order.placed_at, state: "done" },
      { key: "confirmed", at: order.confirmed_at, state: "done" },
      { key: "shipped", at: order.shipped_at, state: "done" },
      { key: "delivery_failed", at: order.delivery_failed_at, state: "current" },
    ];
  }

  const idx = happy.indexOf(order.status as (typeof happy)[number]);
  const currentIdx = idx >= 0 ? idx : 0;
  return happy.map((key, i) => ({
    key,
    at: stamps[key],
    state: i < currentIdx ? "done" : i === currentIdx ? "current" : "upcoming",
  }));
}

export function OrderDetailPanel({ orderId }: { orderId: string }) {
  const t = useTranslations("orders");
  const locale = useLocale();
  const autoPayStarted = useRef(false);
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [paying, setPaying] = useState(false);
  const [returning, setReturning] = useState(false);
  const [returnDone, setReturnDone] = useState(false);

  const load = useCallback(async () => {
    setOrder(await fetchMyOrder(orderId));
  }, [orderId]);

  const onPay = useCallback(async () => {
    setPaying(true);
    setError(null);
    try {
      const started = await startOrderPayment(orderId);
      window.location.assign(started.redirect_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("payFailed"));
      setPaying(false);
    }
  }, [orderId, t]);

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

  useEffect(() => {
    if (!order || autoPayStarted.current || typeof window === "undefined") {
      return;
    }
    const wantsPay = new URLSearchParams(window.location.search).get("pay") === "1";
    if (!wantsPay) {
      return;
    }
    if (
      order.status !== "pending_payment" ||
      (order.payment_method !== "bkash" && order.payment_method !== "sslcommerz")
    ) {
      return;
    }
    autoPayStarted.current = true;
    void onPay();
  }, [order, onPay]);

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

  async function onRequestReturn() {
    if (!order) {
      return;
    }
    const reason = window.prompt(t("returnReasonPrompt"), "defective")?.trim();
    if (!reason) {
      return;
    }
    setReturning(true);
    setError(null);
    try {
      await createReturnRequest(order.id, {
        reason_code: reason,
        items: order.items.map((item) => ({ order_item_id: item.id, qty: item.qty })),
      });
      setReturnDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("returnFailed"));
    } finally {
      setReturning(false);
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
  const steps = buildTrackSteps(order);

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
        {order.status === "pending_payment" &&
        (order.payment_method === "bkash" || order.payment_method === "sslcommerz") ? (
          <button
            type="button"
            disabled={paying}
            onClick={() => void onPay()}
            className="mt-md rounded-sm bg-sage px-md py-sm text-sm font-medium text-white hover:bg-sage-deep disabled:opacity-60"
          >
            {paying ? t("paying") : t("payNow")}
          </button>
        ) : null}
        <p className="mt-md flex flex-wrap gap-sm text-sm">
          <a
            href={`/api/v1/orders/${order.id}/invoice.pdf`}
            className="text-sage underline"
          >
            {t("downloadInvoice")}
          </a>
        </p>
        {order.status === "delivered" &&
        (order.payment_status === "paid" || order.payment_status === "collected") &&
        !returnDone ? (
          <button
            type="button"
            disabled={returning}
            onClick={() => void onRequestReturn()}
            className="mt-sm rounded-sm border border-line px-md py-sm text-sm text-ink disabled:opacity-60"
          >
            {returning ? t("returnWorking") : t("requestReturn")}
          </button>
        ) : null}
        {returnDone ? <p className="mt-sm text-sm text-ok">{t("returnSubmitted")}</p> : null}
      </Reveal>

      <Reveal>
        <h3 className="text-sm font-semibold text-ink">{t("trackingTitle")}</h3>
        {order.courier_name || order.tracking_number ? (
          <p className="mt-sm text-sm text-ink">
            {t("trackingLine", {
              courier: order.courier_name ?? "—",
              tracking: order.tracking_number ?? "—",
            })}
          </p>
        ) : (
          <p className="mt-sm text-sm text-muted">{t("trackingPending")}</p>
        )}
        <ol className="mt-md space-y-0 border-l border-line pl-md">
          {steps.map((step) => (
            <li key={step.key} className="relative pb-md last:pb-0">
              <span
                aria-hidden
                className={
                  step.state === "done"
                    ? "absolute -left-[1.3125rem] top-1 h-2.5 w-2.5 rounded-full bg-sage"
                    : step.state === "current"
                      ? "absolute -left-[1.3125rem] top-1 h-2.5 w-2.5 rounded-full bg-ink ring-2 ring-sage/40"
                      : "absolute -left-[1.3125rem] top-1 h-2.5 w-2.5 rounded-full border border-line bg-paper"
                }
              />
              <p
                className={
                  step.state === "upcoming"
                    ? "text-sm text-muted"
                    : "text-sm font-medium text-ink"
                }
              >
                {t(`status.${step.key}`)}
              </p>
              {step.at ? (
                <p className="text-xs text-muted">{new Date(step.at).toLocaleString()}</p>
              ) : step.state === "upcoming" ? (
                <p className="text-xs text-muted">{t("stepUpcoming")}</p>
              ) : null}
            </li>
          ))}
        </ol>
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

      {order.events.length > 0 ? (
        <Reveal>
          <h3 className="text-sm font-semibold text-ink">{t("historyTitle")}</h3>
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
      ) : null}

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

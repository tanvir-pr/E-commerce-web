"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { fetchMe, isStaff, type Me } from "@/lib/api";
import { formatBdt } from "@/lib/catalog";
import {
  fetchAdminOrder,
  fetchAdminOrders,
  transitionAdminOrder,
  type Order,
  type OrderSummary,
} from "@/lib/orders";

const FILTERS = [
  "pending_payment",
  "confirmed",
  "shipped",
  "delivered",
  "cancelled",
  "all",
] as const;

export function AdminOrders() {
  const t = useTranslations("adminOrders");
  const to = useTranslations("orders");
  const ta = useTranslations("admin");
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [status, setStatus] = useState<(typeof FILTERS)[number]>("confirmed");
  const [items, setItems] = useState<OrderSummary[]>([]);
  const [selected, setSelected] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      setItems(await fetchAdminOrders(status));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loadFailed"));
    }
  }, [status, t]);

  useEffect(() => {
    let active = true;
    void (async () => {
      const current = await fetchMe();
      if (!active) {
        return;
      }
      setMe(current);
      if (!isStaff(current)) {
        setError(ta("forbidden"));
        return;
      }
      await load();
    })();
    return () => {
      active = false;
    };
  }, [load, ta]);

  async function openDetail(id: string) {
    setPending(true);
    setError(null);
    try {
      setSelected(await fetchAdminOrder(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loadFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onTransition(toStatus: string) {
    if (!selected) {
      return;
    }
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      const next = await transitionAdminOrder(selected.id, toStatus);
      setSelected(next);
      setMessage(t("transitioned", { status: toStatus }));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  if (me === undefined) {
    return <p className="text-sm text-muted">{ta("loading")}</p>;
  }
  if (error && !isStaff(me)) {
    return (
      <p role="alert" className="text-sm text-danger">
        {error}
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-lg">
      <div className="flex flex-wrap gap-xs">
        {FILTERS.map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setStatus(key)}
            className={
              status === key
                ? "rounded-sm bg-ink px-sm py-xs text-sm text-paper"
                : "rounded-sm px-sm py-xs text-sm text-muted hover:text-ink"
            }
          >
            {key === "all" ? t("filter.all") : to(`status.${key}`)}
          </button>
        ))}
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-sm border border-line px-sm py-xs text-sm"
        >
          {t("refresh")}
        </button>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="text-sm text-ok">
          {message}
        </p>
      ) : null}

      {items.length === 0 ? (
        <p className="text-sm text-muted">{t("empty")}</p>
      ) : (
        <ul className="divide-y divide-line border border-line">
          {items.map((row) => (
            <li
              key={row.id}
              className="flex flex-wrap items-center justify-between gap-sm px-sm py-sm text-sm"
            >
              <div>
                <p className="font-medium text-ink">
                  {row.order_number} · {to(`status.${row.status}`)}
                </p>
                <p className="text-xs text-muted">
                  {row.user_email ?? "—"} · {formatBdt(row.total_poisha)} ·{" "}
                  {new Date(row.placed_at).toLocaleString()}
                </p>
              </div>
              <button
                type="button"
                disabled={pending}
                onClick={() => void openDetail(row.id)}
                className="rounded-sm border border-line px-sm py-xs disabled:opacity-60"
              >
                {t("view")}
              </button>
            </li>
          ))}
        </ul>
      )}

      {selected ? (
        <div className="border border-line p-md">
          <div className="flex flex-wrap items-center justify-between gap-sm">
            <h2 className="text-sm font-semibold text-ink">
              {selected.order_number} · {to(`status.${selected.status}`)}
            </h2>
            <button type="button" onClick={() => setSelected(null)} className="text-sm underline">
              {t("close")}
            </button>
          </div>
          <ul className="mt-md divide-y divide-line text-sm">
            {selected.items.map((item) => (
              <li key={item.id} className="flex justify-between gap-md py-sm">
                <span>
                  {item.product_name} × {item.qty}
                </span>
                <span>{formatBdt(item.line_total_poisha)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-md text-sm font-medium text-ink">
            {t("total")} · {formatBdt(selected.total_poisha)}
          </p>
          <p className="mt-xs text-xs text-muted">
            {selected.payment_method ?? "—"}
            {selected.payment_status ? ` · ${selected.payment_status}` : ""}
          </p>
          {selected.reservation_expires_at && selected.status === "pending_payment" ? (
            <p className="mt-xs text-xs text-muted">
              {t("reservationHold", {
                when: new Date(selected.reservation_expires_at).toLocaleString(),
              })}
            </p>
          ) : null}
          {selected.allowed_transitions.length > 0 ? (
            <div className="mt-md flex flex-wrap gap-xs">
              {selected.allowed_transitions.map((next) => (
                <button
                  key={next}
                  type="button"
                  disabled={pending}
                  onClick={() => void onTransition(next)}
                  className="rounded-sm border border-line px-sm py-xs text-sm disabled:opacity-60"
                >
                  {t("markAs", { status: to(`status.${next}`) })}
                </button>
              ))}
            </div>
          ) : null}
          <ol className="mt-md divide-y divide-line border-t border-line text-xs text-muted">
            {selected.events.map((event) => (
              <li key={event.id} className="py-sm">
                {event.from_status ?? "—"} → {event.to_status}
                {event.note ? ` · ${event.note}` : ""} ·{" "}
                {new Date(event.created_at).toLocaleString()}
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </div>
  );
}

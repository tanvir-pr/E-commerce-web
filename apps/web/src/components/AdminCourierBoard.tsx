"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import { fetchMe, isStaff, type Me } from "@/lib/api";
import { formatBdt } from "@/lib/catalog";
import {
  fetchAdminOrders,
  packAdminOrder,
  transitionAdminOrder,
  type OrderSummary,
} from "@/lib/orders";

export function AdminCourierBoard() {
  const t = useTranslations("adminCourier");
  const to = useTranslations("orders");
  const ta = useTranslations("admin");
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [confirmed, setConfirmed] = useState<OrderSummary[]>([]);
  const [shipped, setShipped] = useState<OrderSummary[]>([]);
  const [delivered, setDelivered] = useState<OrderSummary[]>([]);
  const [failed, setFailed] = useState<OrderSummary[]>([]);
  const [returned, setReturned] = useState<OrderSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [shipForm, setShipForm] = useState<{
    id: string;
    courier: string;
    tracking: string;
  } | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [c, s, d, f, r] = await Promise.all([
        fetchAdminOrders("confirmed"),
        fetchAdminOrders("shipped"),
        fetchAdminOrders("delivered"),
        fetchAdminOrders("delivery_failed"),
        fetchAdminOrders("returned"),
      ]);
      setConfirmed(c);
      setShipped(s);
      setDelivered(d);
      setFailed(f);
      setReturned(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loadFailed"));
    }
  }, [t]);

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

  const columns = useMemo(() => {
    const toPack = confirmed.filter((row) => !row.packed_at);
    const packed = confirmed.filter((row) => Boolean(row.packed_at));
    return [
      { key: "to_pack" as const, items: toPack },
      { key: "packed" as const, items: packed },
      { key: "shipped" as const, items: shipped },
      { key: "failed" as const, items: failed },
      { key: "delivered" as const, items: delivered },
      { key: "returned" as const, items: returned },
    ];
  }, [confirmed, shipped, delivered, failed, returned]);

  async function onPack(id: string) {
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      await packAdminOrder(id);
      setMessage(t("packed"));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onShip() {
    if (!shipForm) {
      return;
    }
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      await transitionAdminOrder(shipForm.id, "shipped", {
        courier_name: shipForm.courier,
        tracking_number: shipForm.tracking,
      });
      setShipForm(null);
      setMessage(t("shipped"));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onTransition(id: string, toStatus: string, okMessage: string) {
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      await transitionAdminOrder(id, toStatus);
      setMessage(okMessage);
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
      <div className="flex flex-wrap items-center justify-between gap-sm">
        <p className="text-sm text-muted">{t("hint")}</p>
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

      {shipForm ? (
        <div className="border border-line p-md">
          <h2 className="text-sm font-semibold text-ink">{t("shipTitle")}</h2>
          <div className="mt-sm grid gap-sm md:grid-cols-2">
            <label className="flex flex-col gap-2xs text-sm">
              <span className="text-muted">{t("courier")}</span>
              <input
                value={shipForm.courier}
                onChange={(e) => setShipForm({ ...shipForm, courier: e.target.value })}
                className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
                placeholder="Pathao"
              />
            </label>
            <label className="flex flex-col gap-2xs text-sm">
              <span className="text-muted">{t("tracking")}</span>
              <input
                value={shipForm.tracking}
                onChange={(e) => setShipForm({ ...shipForm, tracking: e.target.value })}
                className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
                placeholder="PT-…"
              />
            </label>
          </div>
          <div className="mt-md flex gap-xs">
            <button
              type="button"
              disabled={pending || !shipForm.courier.trim() || !shipForm.tracking.trim()}
              onClick={() => void onShip()}
              className="rounded-sm bg-ink px-sm py-xs text-sm text-paper disabled:opacity-60"
            >
              {t("confirmShip")}
            </button>
            <button
              type="button"
              onClick={() => setShipForm(null)}
              className="rounded-sm border border-line px-sm py-xs text-sm"
            >
              {t("cancel")}
            </button>
          </div>
        </div>
      ) : null}

      <div className="grid gap-md xl:grid-cols-3 2xl:grid-cols-6">
        {columns.map((col) => (
          <section key={col.key} className="min-w-0 border border-line bg-surface">
            <header className="border-b border-line px-sm py-sm">
              <h2 className="text-sm font-semibold text-ink">
                {t(`columns.${col.key}`)} · {col.items.length}
              </h2>
            </header>
            <ul className="flex max-h-[70vh] flex-col gap-sm overflow-y-auto p-sm">
              {col.items.length === 0 ? (
                <li className="text-xs text-muted">{t("emptyColumn")}</li>
              ) : (
                col.items.map((row) => (
                  <li key={row.id} className="border border-line p-sm text-sm">
                    <p className="font-medium text-ink">{row.order_number}</p>
                    <p className="mt-2xs text-xs text-muted">
                      {formatBdt(row.total_poisha)}
                      {row.payment_method ? ` · ${row.payment_method}` : ""}
                      {row.shipping_zone_slug ? ` · ${row.shipping_zone_slug}` : ""}
                    </p>
                    <p className="mt-2xs text-xs text-muted">
                      {t("age", { hours: row.age_hours ?? 0 })}
                      {row.courier_name ? ` · ${row.courier_name}` : ""}
                      {row.tracking_number ? ` · ${row.tracking_number}` : ""}
                    </p>
                    <div className="mt-sm flex flex-wrap gap-xs">
                      {col.key === "to_pack" ? (
                        <button
                          type="button"
                          disabled={pending}
                          onClick={() => void onPack(row.id)}
                          className="rounded-sm border border-line px-sm py-xs text-xs disabled:opacity-60"
                        >
                          {t("markPacked")}
                        </button>
                      ) : null}
                      {col.key === "to_pack" || col.key === "packed" ? (
                        <button
                          type="button"
                          disabled={pending}
                          onClick={() =>
                            setShipForm({
                              id: row.id,
                              courier: row.courier_name ?? "",
                              tracking: row.tracking_number ?? "",
                            })
                          }
                          className="rounded-sm border border-line px-sm py-xs text-xs disabled:opacity-60"
                        >
                          {t("ship")}
                        </button>
                      ) : null}
                      {col.key === "shipped" ? (
                        <>
                          <button
                            type="button"
                            disabled={pending}
                            onClick={() => void onTransition(row.id, "delivered", t("delivered"))}
                            className="rounded-sm border border-line px-sm py-xs text-xs disabled:opacity-60"
                          >
                            {t("markDelivered")}
                          </button>
                          <button
                            type="button"
                            disabled={pending}
                            onClick={() => void onTransition(row.id, "delivery_failed", t("failed"))}
                            className="rounded-sm border border-line px-sm py-xs text-xs disabled:opacity-60"
                          >
                            {t("markFailed")}
                          </button>
                          <button
                            type="button"
                            disabled={pending}
                            onClick={() => void onTransition(row.id, "returned", t("returnedOk"))}
                            className="rounded-sm border border-line px-sm py-xs text-xs disabled:opacity-60"
                          >
                            {t("markReturned")}
                          </button>
                        </>
                      ) : null}
                      {col.key === "failed" ? (
                        <>
                          <button
                            type="button"
                            disabled={pending}
                            onClick={() =>
                              setShipForm({
                                id: row.id,
                                courier: row.courier_name ?? "",
                                tracking: row.tracking_number ?? "",
                              })
                            }
                            className="rounded-sm border border-line px-sm py-xs text-xs disabled:opacity-60"
                          >
                            {t("retryShip")}
                          </button>
                          <button
                            type="button"
                            disabled={pending}
                            onClick={() => void onTransition(row.id, "returned", t("returnedOk"))}
                            className="rounded-sm border border-line px-sm py-xs text-xs disabled:opacity-60"
                          >
                            {t("markReturned")}
                          </button>
                        </>
                      ) : null}
                    </div>
                    <p className="mt-2xs text-[11px] text-muted">
                      {to(`status.${row.status}`)}
                    </p>
                  </li>
                ))
              )}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}

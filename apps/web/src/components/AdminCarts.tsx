"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { fetchMe, isStaff, type Me } from "@/lib/api";
import {
  clearAdminCart,
  fetchAdminCart,
  fetchAdminCarts,
  type AdminCartSummary,
  type CartItem,
} from "@/lib/cart";
import { formatBdt } from "@/lib/catalog";

export function AdminCarts() {
  const t = useTranslations("adminCarts");
  const ta = useTranslations("admin");
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [status, setStatus] = useState("abandoned");
  const [items, setItems] = useState<AdminCartSummary[]>([]);
  const [abandonHours, setAbandonHours] = useState(72);
  const [selected, setSelected] = useState<(AdminCartSummary & { items: CartItem[] }) | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const body = await fetchAdminCarts(status);
      setItems(body.items);
      setAbandonHours(body.abandon_after_hours);
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
      setSelected(await fetchAdminCart(id));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loadFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onClear(id: string) {
    if (!window.confirm(t("clearConfirm"))) {
      return;
    }
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      await clearAdminCart(id);
      setMessage(t("cleared"));
      setSelected(null);
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
      <p className="text-sm text-muted">{t("hint", { hours: abandonHours })}</p>
      <div className="flex flex-wrap gap-xs">
        {(["abandoned", "active", "cleared", "all"] as const).map((key) => (
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
            {t(`filter.${key}`)}
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
                  {row.user_email ?? t("guest")} · {row.status}
                </p>
                <p className="text-xs text-muted">
                  {t("summary", {
                    count: row.item_count,
                    total: formatBdt(row.subtotal_poisha),
                    when: new Date(row.last_activity_at).toLocaleString(),
                  })}
                </p>
              </div>
              <div className="flex gap-xs">
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => void openDetail(row.id)}
                  className="rounded-sm border border-line px-sm py-xs disabled:opacity-60"
                >
                  {t("view")}
                </button>
                {row.status !== "cleared" ? (
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => void onClear(row.id)}
                    className="rounded-sm border border-danger px-sm py-xs text-danger disabled:opacity-60"
                  >
                    {t("clear")}
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}

      {selected ? (
        <div className="border border-line p-md">
          <div className="flex flex-wrap items-center justify-between gap-sm">
            <h2 className="text-sm font-semibold text-ink">
              {t("detailTitle")} · {selected.id.slice(0, 8)}
            </h2>
            <button type="button" onClick={() => setSelected(null)} className="text-sm underline">
              {t("close")}
            </button>
          </div>
          <ul className="mt-md divide-y divide-line text-sm">
            {selected.items.map((item) => (
              <li key={item.id} className="flex justify-between gap-md py-sm">
                <span>
                  {item.product_name} · {item.sku} × {item.qty}
                </span>
                <span>{formatBdt(item.line_total_poisha)}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

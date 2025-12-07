"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  approveAdminReturn,
  fetchAdminReturns,
  rejectAdminReturn,
  type ReturnRequest,
} from "@/lib/orders";
import { formatBdt } from "@/lib/catalog";

export function AdminReturns() {
  const t = useTranslations("adminReturns");
  const [items, setItems] = useState<ReturnRequest[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setItems(await fetchAdminReturns("pending"));
  }, []);

  useEffect(() => {
    void (async () => {
      try {
        await load();
      } catch (err) {
        setError(err instanceof Error ? err.message : t("loadFailed"));
      }
    })();
  }, [load, t]);

  async function onApprove(id: string) {
    setPending(true);
    setError(null);
    try {
      await approveAdminReturn(id, "Approved");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onReject(id: string) {
    const note = window.prompt(t("rejectPrompt"), "")?.trim();
    if (!note) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      await rejectAdminReturn(id, note);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-md">
      <p className="text-sm text-muted">{t("hint")}</p>
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      <button
        type="button"
        onClick={() => void load()}
        className="w-fit text-sm text-sage underline"
      >
        {t("refresh")}
      </button>
      {items.length === 0 ? (
        <p className="text-sm text-muted">{t("empty")}</p>
      ) : (
        <ul className="divide-y divide-line border-t border-line text-sm">
          {items.map((row) => (
            <li key={row.id} className="flex flex-col gap-sm py-md md:flex-row md:items-center md:justify-between">
              <div>
                <p className="font-medium text-ink">
                  {row.order_number ?? row.order_id} · {row.reason_code}
                </p>
                <p className="text-muted">
                  {formatBdt(row.refund_poisha)} · {new Date(row.created_at).toLocaleString()}
                </p>
                {row.customer_note ? (
                  <p className="text-xs text-muted">{row.customer_note}</p>
                ) : null}
              </div>
              <div className="flex gap-sm">
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => void onApprove(row.id)}
                  className="rounded-sm bg-sage px-sm py-2xs text-xs text-white disabled:opacity-60"
                >
                  {t("approve")}
                </button>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => void onReject(row.id)}
                  className="rounded-sm border border-danger px-sm py-2xs text-xs text-danger disabled:opacity-60"
                >
                  {t("reject")}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

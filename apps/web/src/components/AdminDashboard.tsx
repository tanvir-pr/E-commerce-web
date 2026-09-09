"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { fetchMe, isStaff, type Me } from "@/lib/api";
import { formatBdt } from "@/lib/catalog";
import {
  adminMetricsCsvUrl,
  fetchDashboardMetrics,
  type DashboardMetrics,
} from "@/lib/orders";

type AuditItem = {
  id: string;
  action: string;
  actor_user_id: string | null;
  subject_type: string | null;
  subject_id: string | null;
  created_at: string;
};

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

export function AdminDashboard() {
  const t = useTranslations("admin");
  const tm = useTranslations("adminMetrics");
  const locale = useLocale();
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [audit, setAudit] = useState<AuditItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [appliedFrom, setAppliedFrom] = useState("");
  const [appliedTo, setAppliedTo] = useState("");

  const load = useCallback(
    async (rangeFrom: string, rangeTo: string) => {
      const range =
        rangeFrom || rangeTo
          ? { from: rangeFrom || undefined, to: rangeTo || undefined }
          : undefined;
      const [dash, auditRes] = await Promise.all([
        fetchDashboardMetrics(range),
        fetch("/api/v1/admin/audit", { credentials: "include", cache: "no-store" }),
      ]);
      setMetrics(dash);
      if (auditRes.ok) {
        const body = (await auditRes.json()) as { items: AuditItem[] };
        setAudit(body.items);
      }
    },
    [],
  );

  useEffect(() => {
    let active = true;
    void (async () => {
      const current = await fetchMe();
      if (!active) {
        return;
      }
      setMe(current);
      if (!isStaff(current)) {
        setError(t("forbidden"));
        return;
      }
      try {
        await load("", "");
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : tm("loadFailed"));
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load, t, tm]);

  async function applyRange() {
    setError(null);
    try {
      setAppliedFrom(from);
      setAppliedTo(to);
      await load(from, to);
    } catch (err) {
      setError(err instanceof Error ? err.message : tm("loadFailed"));
    }
  }

  async function clearRange() {
    setFrom("");
    setTo("");
    setAppliedFrom("");
    setAppliedTo("");
    setError(null);
    try {
      await load("", "");
    } catch (err) {
      setError(err instanceof Error ? err.message : tm("loadFailed"));
    }
  }

  if (me === undefined) {
    return <p className="text-sm text-muted">{t("loading")}</p>;
  }
  if (error && !metrics) {
    return (
      <p role="alert" className="text-sm text-danger">
        {error}
      </p>
    );
  }

  const period = metrics?.last_7_days;
  const csvHref = adminMetricsCsvUrl(
    appliedFrom || appliedTo
      ? { from: appliedFrom || undefined, to: appliedTo || undefined }
      : undefined,
  );

  return (
    <div className="flex flex-col gap-lg">
      <p className="text-sm text-ink">
        {t("signedIn", { email: me?.email ?? "" })}
        {me?.totp_enabled ? ` · ${t("totpOn")}` : ""}
      </p>

      <div className="flex flex-wrap items-end gap-sm">
        <label className="flex flex-col gap-2xs text-sm">
          <span className="text-muted">{tm("from")}</span>
          <input
            type="date"
            value={from}
            onChange={(e) => setFrom(e.target.value)}
            className="border border-line bg-surface px-sm py-2xs"
          />
        </label>
        <label className="flex flex-col gap-2xs text-sm">
          <span className="text-muted">{tm("to")}</span>
          <input
            type="date"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            className="border border-line bg-surface px-sm py-2xs"
          />
        </label>
        <button
          type="button"
          onClick={() => void applyRange()}
          className="rounded-sm bg-ink px-md py-2xs text-sm text-paper"
        >
          {tm("applyRange")}
        </button>
        <button
          type="button"
          onClick={() => void clearRange()}
          className="rounded-sm border border-line px-md py-2xs text-sm"
        >
          {tm("clearRange")}
        </button>
        <a
          href={csvHref}
          className="rounded-sm border border-line px-md py-2xs text-sm text-ink"
        >
          {tm("exportCsv")}
        </a>
        <Link href={`/${locale}/admin/launch`} className="text-sm text-sage underline">
          {tm("openLaunch")}
        </Link>
      </div>
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      {metrics && period ? (
        <>
          <div className="grid gap-sm sm:grid-cols-2 lg:grid-cols-4">
            <div className="border border-line p-sm">
              <p className="text-xs text-muted">{tm("todayRevenue")}</p>
              <p className="mt-2xs text-lg font-semibold text-ink">
                {formatBdt(metrics.today.revenue_poisha)}
              </p>
              <p className="text-xs text-muted">
                {tm("ordersCount", { count: metrics.today.order_count })}
              </p>
            </div>
            <div className="border border-line p-sm">
              <p className="text-xs text-muted">{tm("weekRevenue")}</p>
              <p className="mt-2xs text-lg font-semibold text-ink">
                {formatBdt(period.revenue_poisha)}
              </p>
              <p className="text-xs text-muted">
                AOV {formatBdt(period.aov_poisha)} · COD {pct(period.cod_share)}
              </p>
            </div>
            <div className="border border-line p-sm">
              <p className="text-xs text-muted">{tm("monthRevenue")}</p>
              <p className="mt-2xs text-lg font-semibold text-ink">
                {formatBdt(metrics.last_30_days.revenue_poisha)}
              </p>
              <p className="text-xs text-muted">
                {tm("cancelRate", { rate: pct(metrics.last_30_days.cancel_rate) })}
              </p>
            </div>
            <div className="border border-line p-sm">
              <p className="text-xs text-muted">
                {metrics.custom ? tm("customRevenue") : tm("unshipped")}
              </p>
              <p className="mt-2xs text-lg font-semibold text-ink">
                {metrics.custom
                  ? formatBdt(metrics.custom.revenue_poisha)
                  : metrics.unshipped_confirmed}
              </p>
              {metrics.custom ? (
                <p className="text-xs text-muted">
                  {tm("ordersCount", { count: metrics.custom.order_count })}
                </p>
              ) : (
                <Link href={`/${locale}/admin/courier`} className="text-xs text-sage underline">
                  {tm("openCourier")}
                </Link>
              )}
            </div>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-ink">{tm("funnelTitle")}</h2>
            <ul className="mt-sm grid gap-sm sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
              {(
                [
                  "pending_payment",
                  "confirmed",
                  "shipped",
                  "delivered",
                  "delivery_failed",
                  "returned",
                  "cancelled",
                ] as const
              ).map((key) => (
                <li key={key} className="border border-line px-sm py-sm text-sm">
                  <p className="text-xs text-muted">{tm(`funnel.${key}`)}</p>
                  <p className="font-semibold text-ink">{metrics.funnel[key]}</p>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h2 className="text-sm font-semibold text-ink">{tm("alertsTitle")}</h2>
            <ul className="mt-sm grid gap-sm sm:grid-cols-2 lg:grid-cols-4">
              <li className="border border-line px-sm py-sm text-sm">
                {tm("alertLowStock", { count: metrics.alerts.low_stock_count })}
              </li>
              <li className="border border-line px-sm py-sm text-sm">
                {tm("alertNearExpiry", { count: metrics.alerts.near_expiry_count })}
              </li>
              <li className="border border-line px-sm py-sm text-sm">
                {tm("alertOverdue", { count: metrics.alerts.overdue_shipments })}
              </li>
              <li className="border border-line px-sm py-sm text-sm">
                {tm("alertAbandoned", {
                  value: formatBdt(metrics.alerts.abandoned_cart_value_poisha),
                })}
              </li>
            </ul>
          </div>

          {metrics.top_products.length > 0 ? (
            <div>
              <h2 className="text-sm font-semibold text-ink">{tm("topProducts")}</h2>
              <ul className="mt-sm divide-y divide-line border border-line text-sm">
                {metrics.top_products.map((row) => (
                  <li key={row.product_id} className="flex justify-between gap-md px-sm py-sm">
                    <span>
                      {row.product_name} · {row.units}u
                    </span>
                    <span>{formatBdt(row.revenue_poisha)}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </>
      ) : null}

      <div>
        <h2 className="text-sm font-semibold text-ink">{t("recentAudit")}</h2>
        {audit.length === 0 ? (
          <p className="mt-sm text-sm text-muted">{t("noAudit")}</p>
        ) : (
          <ul className="mt-sm divide-y divide-line border border-line">
            {audit.map((item) => (
              <li
                key={item.id}
                className="flex flex-col gap-xs px-sm py-sm text-sm md:flex-row md:justify-between"
              >
                <span className="font-mono text-ink">{item.action}</span>
                <span className="text-muted">{new Date(item.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { formatBdt } from "@/lib/catalog";
import { fetchAdminCategories, type CategoryNode } from "@/lib/catalog-admin";
import {
  createCoupon,
  deleteCoupon,
  fetchAdminCoupons,
  patchCoupon,
  type Coupon,
} from "@/lib/coupons";
import { bdtInputToPoisha } from "@/lib/shipping";

function flattenCategories(nodes: CategoryNode[], depth = 0): { id: string; label: string }[] {
  const out: { id: string; label: string }[] = [];
  for (const node of nodes) {
    out.push({ id: node.id, label: `${"—".repeat(depth)}${node.name}` });
    if (node.children?.length) {
      out.push(...flattenCategories(node.children, depth + 1));
    }
  }
  return out;
}

export function AdminCoupons() {
  const t = useTranslations("adminCoupons");
  const [items, setItems] = useState<Coupon[]>([]);
  const [categories, setCategories] = useState<{ id: string; label: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [code, setCode] = useState("");
  const [discountType, setDiscountType] = useState<"percent" | "fixed">("percent");
  const [value, setValue] = useState("10");
  const [minSpend, setMinSpend] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [maxRedemptions, setMaxRedemptions] = useState("");
  const [maxPerUser, setMaxPerUser] = useState("");
  const [expiresAt, setExpiresAt] = useState("");
  const [isActive, setIsActive] = useState(true);

  const load = useCallback(async () => {
    const [coupons, cats] = await Promise.all([
      fetchAdminCoupons(),
      fetchAdminCategories(),
    ]);
    setItems(coupons);
    setCategories(flattenCategories(cats));
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

  function payload() {
    const parsedValue = Number.parseInt(value, 10);
    if (!Number.isFinite(parsedValue) || parsedValue < 1) {
      throw new Error(t("valueRequired"));
    }
    return {
      code: code.trim().toUpperCase(),
      discount_type: discountType,
      value: parsedValue,
      min_spend_poisha: minSpend.trim() ? bdtInputToPoisha(minSpend) : null,
      category_id: categoryId || null,
      starts_at: null,
      expires_at: expiresAt ? new Date(expiresAt).toISOString() : null,
      max_redemptions: maxRedemptions.trim()
        ? Number.parseInt(maxRedemptions, 10)
        : null,
      max_per_user: maxPerUser.trim() ? Number.parseInt(maxPerUser, 10) : null,
      is_active: isActive,
    };
  }

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await createCoupon(payload());
      setCode("");
      setValue("10");
      setMinSpend("");
      setCategoryId("");
      setMaxRedemptions("");
      setMaxPerUser("");
      setExpiresAt("");
      setIsActive(true);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onToggle(row: Coupon) {
    setPending(true);
    setError(null);
    try {
      await patchCoupon(row.id, {
        code: row.code,
        discount_type: row.discount_type === "fixed" ? "fixed" : "percent",
        value: row.value,
        min_spend_poisha: row.min_spend_poisha,
        category_id: row.category_id,
        starts_at: row.starts_at,
        expires_at: row.expires_at,
        max_redemptions: row.max_redemptions,
        max_per_user: row.max_per_user,
        is_active: !row.is_active,
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onDelete(row: Coupon) {
    if (!window.confirm(t("confirmDelete", { code: row.code }))) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      await deleteCoupon(row.id);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      <p className="text-sm text-muted">{t("hint")}</p>
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      <form onSubmit={(e) => void onCreate(e)} className="flex flex-col gap-sm border-t border-line pt-md">
        <h2 className="text-sm font-semibold text-ink">{t("createTitle")}</h2>
        <div className="grid gap-sm md:grid-cols-2">
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("code")}</span>
            <input
              value={code}
              onChange={(e) => setCode(e.target.value)}
              required
              className="rounded-sm border border-line px-sm py-2xs"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("type")}</span>
            <select
              value={discountType}
              onChange={(e) => setDiscountType(e.target.value as "percent" | "fixed")}
              className="rounded-sm border border-line px-sm py-2xs"
            >
              <option value="percent">{t("typePercent")}</option>
              <option value="fixed">{t("typeFixed")}</option>
            </select>
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">
              {discountType === "percent" ? t("valuePercent") : t("valueFixed")}
            </span>
            <input
              value={value}
              onChange={(e) => setValue(e.target.value)}
              required
              className="rounded-sm border border-line px-sm py-2xs"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("minSpend")}</span>
            <input
              value={minSpend}
              onChange={(e) => setMinSpend(e.target.value)}
              placeholder="0"
              className="rounded-sm border border-line px-sm py-2xs"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("category")}</span>
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value)}
              className="rounded-sm border border-line px-sm py-2xs"
            >
              <option value="">{t("anyCategory")}</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.label}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("expiresAt")}</span>
            <input
              type="datetime-local"
              value={expiresAt}
              onChange={(e) => setExpiresAt(e.target.value)}
              className="rounded-sm border border-line px-sm py-2xs"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("maxRedemptions")}</span>
            <input
              value={maxRedemptions}
              onChange={(e) => setMaxRedemptions(e.target.value)}
              className="rounded-sm border border-line px-sm py-2xs"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("maxPerUser")}</span>
            <input
              value={maxPerUser}
              onChange={(e) => setMaxPerUser(e.target.value)}
              className="rounded-sm border border-line px-sm py-2xs"
            />
          </label>
        </div>
        <label className="flex items-center gap-sm text-sm text-muted">
          <input
            type="checkbox"
            checked={isActive}
            onChange={(e) => setIsActive(e.target.checked)}
          />
          {t("active")}
        </label>
        <button
          type="submit"
          disabled={pending}
          className="w-fit rounded-sm bg-sage px-md py-sm text-sm text-white disabled:opacity-60"
        >
          {pending ? t("working") : t("create")}
        </button>
      </form>

      <div className="border-t border-line pt-md">
        <div className="mb-sm flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink">{t("listTitle")}</h2>
          <button
            type="button"
            onClick={() => void load()}
            className="text-sm text-sage underline"
          >
            {t("refresh")}
          </button>
        </div>
        {items.length === 0 ? (
          <p className="text-sm text-muted">{t("empty")}</p>
        ) : (
          <ul className="divide-y divide-line border-t border-line text-sm">
            {items.map((row) => (
              <li
                key={row.id}
                className="flex flex-col gap-sm py-md md:flex-row md:items-center md:justify-between"
              >
                <div>
                  <p className="font-medium text-ink">
                    {row.code}{" "}
                    <span className="text-muted">
                      ·{" "}
                      {row.discount_type === "percent"
                        ? t("summaryPercent", { value: row.value })
                        : t("summaryFixed", { value: formatBdt(row.value) })}
                    </span>
                    {!row.is_active ? (
                      <span className="ml-xs text-danger">· {t("inactive")}</span>
                    ) : null}
                  </p>
                  <p className="text-muted">
                    {t("redemptions", { count: row.redemption_count })}
                    {row.min_spend_poisha != null
                      ? ` · ${t("minSpendShort", { value: formatBdt(row.min_spend_poisha) })}`
                      : ""}
                    {row.expires_at
                      ? ` · ${t("expiresShort", { date: new Date(row.expires_at).toLocaleString() })}`
                      : ""}
                  </p>
                </div>
                <div className="flex gap-sm">
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => void onToggle(row)}
                    className="rounded-sm border border-line px-sm py-2xs text-xs disabled:opacity-60"
                  >
                    {row.is_active ? t("deactivate") : t("activate")}
                  </button>
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => void onDelete(row)}
                    className="rounded-sm border border-danger px-sm py-2xs text-xs text-danger disabled:opacity-60"
                  >
                    {t("delete")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

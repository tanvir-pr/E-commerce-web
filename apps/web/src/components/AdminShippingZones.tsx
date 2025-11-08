"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { fetchMe, isStaff, type Me } from "@/lib/api";
import { formatBdt } from "@/lib/catalog";
import {
  bdtInputToPoisha,
  createZone,
  deleteZone,
  fetchAdminZones,
  patchZone,
  poishaToBdtInput,
  quoteShipping,
  type DeliveryZone,
  type ZonePayload,
} from "@/lib/shipping";

type DraftTier = { max_weight_grams: string; charge_bdt: string };

type Draft = {
  slug: string;
  name: string;
  match_districts: string;
  is_default: boolean;
  is_active: boolean;
  sort_order: string;
  free_shipping_threshold_bdt: string;
  tiers: DraftTier[];
};

function emptyDraft(): Draft {
  return {
    slug: "",
    name: "",
    match_districts: "",
    is_default: false,
    is_active: true,
    sort_order: "0",
    free_shipping_threshold_bdt: "",
    tiers: [{ max_weight_grams: "500", charge_bdt: "60" }],
  };
}

function zoneToDraft(zone: DeliveryZone): Draft {
  return {
    slug: zone.slug,
    name: zone.name,
    match_districts: zone.match_districts.join(", "),
    is_default: zone.is_default,
    is_active: zone.is_active,
    sort_order: String(zone.sort_order),
    free_shipping_threshold_bdt: poishaToBdtInput(zone.free_shipping_threshold_poisha),
    tiers: zone.tiers.map((t) => ({
      max_weight_grams: String(t.max_weight_grams),
      charge_bdt: poishaToBdtInput(t.charge_poisha) || "0",
    })),
  };
}

function draftToPayload(draft: Draft): ZonePayload {
  const tiers = draft.tiers
    .map((t) => ({
      max_weight_grams: Number.parseInt(t.max_weight_grams, 10),
      charge_poisha: bdtInputToPoisha(t.charge_bdt) ?? -1,
    }))
    .filter((t) => Number.isFinite(t.max_weight_grams) && t.max_weight_grams > 0 && t.charge_poisha >= 0);
  if (!tiers.length) {
    throw new Error("tiers");
  }
  return {
    slug: draft.slug.trim().toLowerCase(),
    name: draft.name.trim(),
    match_districts: draft.match_districts
      .split(",")
      .map((d) => d.trim())
      .filter(Boolean),
    is_default: draft.is_default,
    is_active: draft.is_active,
    sort_order: Number.parseInt(draft.sort_order, 10) || 0,
    free_shipping_threshold_poisha: bdtInputToPoisha(draft.free_shipping_threshold_bdt),
    tiers,
  };
}

export function AdminShippingZones() {
  const t = useTranslations("adminShipping");
  const ta = useTranslations("admin");
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [zones, setZones] = useState<DeliveryZone[]>([]);
  const [globalThreshold, setGlobalThreshold] = useState(0);
  const [defaultWeight, setDefaultWeight] = useState(100);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>(emptyDraft());
  const [quoteDistrict, setQuoteDistrict] = useState("Dhaka");
  const [quoteWeight, setQuoteWeight] = useState("500");
  const [quoteSubtotal, setQuoteSubtotal] = useState("2000");
  const [quoteResult, setQuoteResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const body = await fetchAdminZones();
      setZones(body.items);
      setGlobalThreshold(body.free_shipping_threshold_poisha);
      setDefaultWeight(body.default_variant_weight_grams);
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

  function startCreate() {
    setEditingId(null);
    setDraft(emptyDraft());
    setMessage(null);
  }

  function startEdit(zone: DeliveryZone) {
    setEditingId(zone.id);
    setDraft(zoneToDraft(zone));
    setMessage(null);
  }

  async function onSave() {
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      const payload = draftToPayload(draft);
      if (editingId) {
        await patchZone(editingId, payload);
        setMessage(t("saved"));
      } else {
        await createZone(payload);
        setMessage(t("created"));
        setDraft(emptyDraft());
      }
      await load();
    } catch (err) {
      setError(
        err instanceof Error && err.message === "tiers"
          ? t("tiersRequired")
          : err instanceof Error
            ? err.message
            : t("saveFailed"),
      );
    } finally {
      setPending(false);
    }
  }

  async function onDelete(zone: DeliveryZone) {
    if (!window.confirm(t("deleteConfirm", { name: zone.name }))) {
      return;
    }
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      await deleteZone(zone.id);
      setMessage(t("deleted"));
      if (editingId === zone.id) {
        startCreate();
      }
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onQuote() {
    setPending(true);
    setError(null);
    setQuoteResult(null);
    try {
      const subtotal = bdtInputToPoisha(quoteSubtotal) ?? 0;
      const weight = Number.parseInt(quoteWeight, 10) || 0;
      const quote = await quoteShipping({
        district: quoteDistrict,
        weight_grams: weight,
        subtotal_poisha: subtotal,
      });
      setQuoteResult(
        t("quoteResult", {
          zone: quote.zone_name,
          weight: quote.total_weight_grams,
          charge: formatBdt(quote.charge_poisha),
          free: quote.free_shipping_applied ? t("yes") : t("no"),
          matched: quote.matched_by,
        }),
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t("quoteFailed"));
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
    <div className="flex flex-col gap-xl">
      <p className="text-sm text-muted">
        {t("hint", {
          threshold: formatBdt(globalThreshold),
          weight: defaultWeight,
        })}
      </p>

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

      <section className="flex flex-col gap-sm">
        <div className="flex flex-wrap items-center justify-between gap-sm">
          <h2 className="text-sm font-semibold text-ink">{t("listTitle")}</h2>
          <button
            type="button"
            onClick={startCreate}
            className="rounded-sm border border-line px-sm py-xs text-sm"
          >
            {t("newZone")}
          </button>
        </div>
        {zones.length === 0 ? (
          <p className="text-sm text-muted">{t("empty")}</p>
        ) : (
          <ul className="divide-y divide-line border border-line">
            {zones.map((zone) => (
              <li
                key={zone.id}
                className="flex flex-wrap items-center justify-between gap-sm px-sm py-sm text-sm"
              >
                <div>
                  <p className="font-medium text-ink">
                    {zone.name}{" "}
                    <span className="text-xs font-normal text-muted">/{zone.slug}</span>
                  </p>
                  <p className="text-xs text-muted">
                    {zone.is_default ? t("defaultBadge") : zone.match_districts.join(", ") || "—"}
                    {" · "}
                    {zone.tiers.length} {t("tiers")}
                    {!zone.is_active ? ` · ${t("inactive")}` : ""}
                  </p>
                </div>
                <div className="flex gap-xs">
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => startEdit(zone)}
                    className="rounded-sm border border-line px-sm py-xs disabled:opacity-60"
                  >
                    {t("edit")}
                  </button>
                  <button
                    type="button"
                    disabled={pending || zone.is_default}
                    onClick={() => void onDelete(zone)}
                    className="rounded-sm border border-danger px-sm py-xs text-danger disabled:opacity-60"
                  >
                    {t("delete")}
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="flex flex-col gap-sm border border-line p-md">
        <h2 className="text-sm font-semibold text-ink">
          {editingId ? t("editTitle") : t("createTitle")}
        </h2>
        <div className="grid gap-sm md:grid-cols-2">
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("name")}</span>
            <input
              value={draft.name}
              onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("slug")}</span>
            <input
              value={draft.slug}
              onChange={(e) => setDraft((d) => ({ ...d, slug: e.target.value }))}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm md:col-span-2">
            <span className="text-muted">{t("districts")}</span>
            <input
              value={draft.match_districts}
              onChange={(e) => setDraft((d) => ({ ...d, match_districts: e.target.value }))}
              placeholder={t("districtsPlaceholder")}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("threshold")}</span>
            <input
              value={draft.free_shipping_threshold_bdt}
              onChange={(e) =>
                setDraft((d) => ({ ...d, free_shipping_threshold_bdt: e.target.value }))
              }
              placeholder={t("thresholdPlaceholder")}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("sortOrder")}</span>
            <input
              type="number"
              value={draft.sort_order}
              onChange={(e) => setDraft((d) => ({ ...d, sort_order: e.target.value }))}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
        </div>
        <div className="flex flex-wrap gap-md text-sm">
          <label className="flex items-center gap-xs">
            <input
              type="checkbox"
              checked={draft.is_default}
              onChange={(e) => setDraft((d) => ({ ...d, is_default: e.target.checked }))}
            />
            {t("isDefault")}
          </label>
          <label className="flex items-center gap-xs">
            <input
              type="checkbox"
              checked={draft.is_active}
              onChange={(e) => setDraft((d) => ({ ...d, is_active: e.target.checked }))}
            />
            {t("isActive")}
          </label>
        </div>

        <div className="mt-sm flex flex-col gap-xs">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-ink">{t("tiersTitle")}</p>
            <button
              type="button"
              onClick={() =>
                setDraft((d) => ({
                  ...d,
                  tiers: [...d.tiers, { max_weight_grams: "", charge_bdt: "" }],
                }))
              }
              className="text-sm underline"
            >
              {t("addTier")}
            </button>
          </div>
          {draft.tiers.map((tier, index) => (
            <div key={index} className="flex flex-wrap items-end gap-sm">
              <label className="flex flex-col gap-2xs text-sm">
                <span className="text-muted">{t("maxGrams")}</span>
                <input
                  type="number"
                  value={tier.max_weight_grams}
                  onChange={(e) =>
                    setDraft((d) => {
                      const tiers = [...d.tiers];
                      tiers[index] = { ...tiers[index], max_weight_grams: e.target.value };
                      return { ...d, tiers };
                    })
                  }
                  className="w-28 rounded-sm border border-line bg-surface px-sm py-xs text-ink"
                />
              </label>
              <label className="flex flex-col gap-2xs text-sm">
                <span className="text-muted">{t("chargeBdt")}</span>
                <input
                  value={tier.charge_bdt}
                  onChange={(e) =>
                    setDraft((d) => {
                      const tiers = [...d.tiers];
                      tiers[index] = { ...tiers[index], charge_bdt: e.target.value };
                      return { ...d, tiers };
                    })
                  }
                  className="w-28 rounded-sm border border-line bg-surface px-sm py-xs text-ink"
                />
              </label>
              {draft.tiers.length > 1 ? (
                <button
                  type="button"
                  onClick={() =>
                    setDraft((d) => ({
                      ...d,
                      tiers: d.tiers.filter((_, i) => i !== index),
                    }))
                  }
                  className="text-sm text-danger underline"
                >
                  {t("removeTier")}
                </button>
              ) : null}
            </div>
          ))}
        </div>

        <button
          type="button"
          disabled={pending}
          onClick={() => void onSave()}
          className="mt-sm w-fit rounded-sm bg-ink px-md py-sm text-sm text-paper disabled:opacity-60"
        >
          {pending ? ta("working") : t("save")}
        </button>
      </section>

      <section className="flex flex-col gap-sm border border-line p-md">
        <h2 className="text-sm font-semibold text-ink">{t("quoteTitle")}</h2>
        <div className="grid gap-sm md:grid-cols-3">
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("quoteDistrict")}</span>
            <input
              value={quoteDistrict}
              onChange={(e) => setQuoteDistrict(e.target.value)}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("quoteWeight")}</span>
            <input
              type="number"
              value={quoteWeight}
              onChange={(e) => setQuoteWeight(e.target.value)}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("quoteSubtotal")}</span>
            <input
              value={quoteSubtotal}
              onChange={(e) => setQuoteSubtotal(e.target.value)}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
        </div>
        <button
          type="button"
          disabled={pending}
          onClick={() => void onQuote()}
          className="w-fit rounded-sm border border-line px-md py-sm text-sm disabled:opacity-60"
        >
          {t("runQuote")}
        </button>
        {quoteResult ? <p className="text-sm text-ink">{quoteResult}</p> : null}
      </section>
    </div>
  );
}

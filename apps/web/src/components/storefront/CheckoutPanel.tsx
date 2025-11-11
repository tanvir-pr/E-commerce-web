"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { Reveal } from "@/components/motion/Reveal";
import {
  apiPost,
  fetchAddresses,
  fetchCsrfToken,
  fetchMe,
  isStaff,
  readProblem,
  type Address,
  type Me,
} from "@/lib/api";
import { formatBdt } from "@/lib/catalog";
import { fetchCheckoutQuote, type CheckoutQuote } from "@/lib/checkout";

export function CheckoutPanel() {
  const t = useTranslations("checkout");
  const locale = useLocale();
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [addressId, setAddressId] = useState<string>("");
  const [quote, setQuote] = useState<CheckoutQuote | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [line1, setLine1] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [phone, setPhone] = useState("");
  const [saveAddress, setSaveAddress] = useState(true);

  const loadAddresses = useCallback(async () => {
    const rows = await fetchAddresses();
    setAddresses(rows);
    const preferred = rows.find((r) => r.is_default) ?? rows[0];
    if (preferred) {
      setAddressId(preferred.id);
    }
  }, []);

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
        await loadAddresses();
      } catch {
        if (active) {
          setError(t("addressLoadFailed"));
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [loadAddresses, t]);

  const verified =
    me != null && (Boolean(me.email_verified_at) || Boolean(me.phone_verified_at));

  async function runQuote(nextAddressId?: string) {
    setPending(true);
    setError(null);
    try {
      const id = nextAddressId ?? addressId;
      const body = id
        ? { address_id: id }
        : {
            line1,
            city,
            district: district || undefined,
            phone: phone || undefined,
            country: "BD",
          };
      if (!id && (!line1.trim() || !city.trim())) {
        throw new Error(t("addressRequired"));
      }
      setQuote(await fetchCheckoutQuote(body));
    } catch (err) {
      setQuote(null);
      setError(err instanceof Error ? err.message : t("quoteFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onCreateAddress(event: FormEvent) {
    event.preventDefault();
    if (!saveAddress) {
      await runQuote("");
      return;
    }
    setPending(true);
    setError(null);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiPost(
        "/api/v1/users/me/addresses",
        {
          line1,
          city,
          district: district || null,
          phone: phone || null,
          country: "BD",
          is_default: addresses.length === 0,
        },
        csrf,
      );
      if (!response.ok) {
        throw new Error(await readProblem(response));
      }
      const created = (await response.json()) as Address;
      await loadAddresses();
      setAddressId(created.id);
      await runQuote(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("addressSaveFailed"));
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

  if (!verified) {
    return (
      <Reveal>
        <p className="text-muted">{t("verifyRequired")}</p>
        <p className="mt-sm text-sm text-muted">{t("verifyHint", { email: me.email })}</p>
        <Link href={`/${locale}/account`} className="mt-md inline-block text-sage underline">
          {t("openAccount")}
        </Link>
      </Reveal>
    );
  }

  return (
    <div className="flex flex-col gap-xl">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}

      <Reveal>
        <h2 className="font-display text-display text-ink">{t("addressTitle")}</h2>
        {addresses.length > 0 ? (
          <ul className="mt-md divide-y divide-line border-t border-line">
            {addresses.map((row) => (
              <li key={row.id} className="flex flex-wrap items-center justify-between gap-sm py-md">
                <label className="flex cursor-pointer items-start gap-sm text-sm">
                  <input
                    type="radio"
                    name="address"
                    checked={addressId === row.id}
                    onChange={() => setAddressId(row.id)}
                    className="mt-1"
                  />
                  <span>
                    <span className="font-medium text-ink">
                      {row.label || row.line1}
                      {row.is_default ? ` · ${t("defaultAddress")}` : ""}
                    </span>
                    <span className="mt-2xs block text-muted">
                      {row.line1}
                      {row.city ? `, ${row.city}` : ""}
                      {row.district ? `, ${row.district}` : ""}
                    </span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-sm text-sm text-muted">{t("noAddresses")}</p>
        )}

        {addresses.length > 0 ? (
          <button
            type="button"
            disabled={pending || !addressId}
            onClick={() => void runQuote()}
            className="mt-md rounded-sm bg-ink px-md py-sm text-sm text-paper disabled:opacity-60"
          >
            {pending ? t("quoting") : t("quote")}
          </button>
        ) : null}
      </Reveal>

      <Reveal>
        <h2 className="font-display text-display text-ink">{t("newAddressTitle")}</h2>
        <form onSubmit={(e) => void onCreateAddress(e)} className="mt-md flex max-w-lg flex-col gap-sm">
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("line1")}</span>
            <input
              required
              value={line1}
              onChange={(e) => setLine1(e.target.value)}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
          <div className="grid gap-sm md:grid-cols-2">
            <label className="flex flex-col gap-2xs text-sm">
              <span className="text-muted">{t("city")}</span>
              <input
                required
                value={city}
                onChange={(e) => setCity(e.target.value)}
                className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
              />
            </label>
            <label className="flex flex-col gap-2xs text-sm">
              <span className="text-muted">{t("district")}</span>
              <input
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
              />
            </label>
          </div>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("phone")}</span>
            <input
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="rounded-sm border border-line bg-surface px-sm py-xs text-ink"
            />
          </label>
          <label className="flex items-center gap-xs text-sm">
            <input
              type="checkbox"
              checked={saveAddress}
              onChange={(e) => setSaveAddress(e.target.checked)}
            />
            {t("saveAddress")}
          </label>
          <button
            type="submit"
            disabled={pending}
            className="w-fit rounded-sm border border-line px-md py-sm text-sm disabled:opacity-60"
          >
            {pending ? t("quoting") : t("quoteWithNew")}
          </button>
        </form>
      </Reveal>

      {quote ? (
        <Reveal>
          <h2 className="font-display text-display text-ink">{t("summaryTitle")}</h2>
          <ul className="mt-md divide-y divide-line border-t border-line text-sm">
            {quote.cart.items.map((item) => (
              <li key={item.id} className="flex justify-between gap-md py-sm">
                <span>
                  {item.product_name} × {item.qty}
                  {!quote.stock.find((s) => s.variant_id === item.variant_id)?.ok ? (
                    <span className="ml-xs text-danger">· {t("stockIssue")}</span>
                  ) : null}
                </span>
                <span>{formatBdt(item.line_total_poisha)}</span>
              </li>
            ))}
          </ul>
          <div className="mt-md flex flex-col gap-2xs border-t border-line pt-md text-sm">
            <p className="flex justify-between">
              <span className="text-muted">{t("merchandise")}</span>
              <span>{formatBdt(quote.merchandise_subtotal_poisha)}</span>
            </p>
            <p className="flex justify-between">
              <span className="text-muted">
                {t("shipping")} · {quote.shipping.zone_name}
                {quote.shipping.free_shipping_applied ? ` · ${t("freeShipping")}` : ""}
              </span>
              <span>{formatBdt(quote.shipping_poisha)}</span>
            </p>
            <p className="flex justify-between text-base font-medium text-ink">
              <span>{t("total")}</span>
              <span>{formatBdt(quote.total_poisha)}</span>
            </p>
          </div>
          {quote.ready ? (
            <p role="status" className="mt-md text-sm text-ok">
              {t("ready")}
            </p>
          ) : (
            <p role="status" className="mt-md text-sm text-danger">
              {t("notReady")}
            </p>
          )}
          <p className="mt-sm text-sm text-muted">{t("placeOrderSoon")}</p>
          {isStaff(me) ? (
            <p className="mt-2xs text-xs text-muted">{t("staffNote")}</p>
          ) : null}
        </Reveal>
      ) : null}
    </div>
  );
}

"use client";

import { FormEvent, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import {
  apiDelete,
  apiPatch,
  apiPost,
  fetchAddresses,
  fetchAuthConfig,
  fetchCsrfToken,
  fetchMe,
  fetchSessions,
  readProblem,
  type Address,
  type AuthConfig,
  type Me,
  type Session,
} from "@/lib/api";

export function AccountPanel() {
  const t = useTranslations("account");
  const locale = useLocale();
  const router = useRouter();
  const [me, setMe] = useState<Me | null | undefined>(undefined);
  const [config, setConfig] = useState<AuthConfig | null>(null);
  const [addresses, setAddresses] = useState<Address[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [displayName, setDisplayName] = useState("");
  const [skinType, setSkinType] = useState("");
  const [concerns, setConcerns] = useState<string[]>([]);
  const [line1, setLine1] = useState("");
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function reload() {
    const [meResult, configResult] = await Promise.all([fetchMe(), fetchAuthConfig()]);
    setMe(meResult);
    setConfig(configResult);
    if (!meResult) {
      return;
    }
    setDisplayName(meResult.display_name ?? "");
    setSkinType(meResult.skin_type ?? "");
    setConcerns(meResult.skin_concerns ?? []);
    const [addressRows, sessionRows] = await Promise.all([fetchAddresses(), fetchSessions()]);
    setAddresses(addressRows);
    setSessions(sessionRows);
  }

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        await reload();
      } catch {
        if (active) {
          setError(t("networkError"));
          setMe(null);
        }
      }
    })();
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (me === undefined) {
    return <p className="text-sm text-muted">{t("loading")}</p>;
  }

  if (!me) {
    return (
      <p className="text-sm text-muted">
        <a href={`/${locale}/login`} className="underline">
          {t("signInFirst")}
        </a>
      </p>
    );
  }

  async function onSaveProfile(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiPatch(
        "/api/v1/users/me",
        {
          display_name: displayName || null,
          skin_type: skinType || null,
          skin_concerns: concerns,
        },
        csrf,
      );
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      setMessage(t("profileSaved"));
      await reload();
    } catch {
      setError(t("networkError"));
    } finally {
      setBusy(false);
    }
  }

  async function onAddAddress(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiPost(
        "/api/v1/users/me/addresses",
        {
          line1,
          city,
          district: district || null,
          country: "BD",
          is_default: addresses.length === 0,
        },
        csrf,
      );
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      setLine1("");
      setCity("");
      setDistrict("");
      await reload();
    } catch {
      setError(t("networkError"));
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteAddress(id: string) {
    setBusy(true);
    setError(null);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiDelete(`/api/v1/users/me/addresses/${id}`, csrf);
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      await reload();
    } catch {
      setError(t("networkError"));
    } finally {
      setBusy(false);
    }
  }

  async function onRevokeSession(id: string) {
    setBusy(true);
    setError(null);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiDelete(`/api/v1/users/me/sessions/${id}`, csrf);
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      await reload();
    } catch {
      setError(t("networkError"));
    } finally {
      setBusy(false);
    }
  }

  async function onLogoutEverywhere() {
    setBusy(true);
    setError(null);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiPost("/api/v1/auth/logout-everywhere", {}, csrf);
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      router.push(`/${locale}/login`);
      router.refresh();
    } catch {
      setError(t("networkError"));
    } finally {
      setBusy(false);
    }
  }

  async function onExport() {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/v1/users/me/export", {
        credentials: "include",
        cache: "no-store",
      });
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "account-export.json";
      anchor.click();
      URL.revokeObjectURL(url);
      setMessage(t("exportDone"));
    } catch {
      setError(t("networkError"));
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteAccount() {
    if (!window.confirm(t("deleteConfirm"))) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiDelete("/api/v1/users/me", csrf);
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      router.push(`/${locale}`);
      router.refresh();
    } catch {
      setError(t("networkError"));
    } finally {
      setBusy(false);
    }
  }

  function toggleConcern(value: string) {
    setConcerns((prev) =>
      prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value],
    );
  }

  return (
    <div className="flex flex-col gap-xl">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {message ? <p className="text-sm text-ok">{message}</p> : null}

      <section className="flex flex-col gap-md">
        <h2 className="text-lg font-semibold text-ink">{t("profileTitle")}</h2>
        <p className="text-sm text-muted">{me.email}</p>
        <form onSubmit={onSaveProfile} className="flex flex-col gap-md">
          <label className="flex flex-col gap-xs text-sm">
            <span>{t("displayName")}</span>
            <input
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
            />
          </label>
          <label className="flex flex-col gap-xs text-sm">
            <span>{t("skinType")}</span>
            <select
              value={skinType}
              onChange={(e) => setSkinType(e.target.value)}
              className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
            >
              <option value="">{t("skinTypeNone")}</option>
              {(config?.skin_types ?? []).map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <fieldset className="flex flex-col gap-xs text-sm">
            <legend>{t("skinConcerns")}</legend>
            <div className="flex flex-wrap gap-sm">
              {(config?.skin_concerns ?? []).map((value) => (
                <label key={value} className="flex items-center gap-xs">
                  <input
                    type="checkbox"
                    checked={concerns.includes(value)}
                    onChange={() => toggleConcern(value)}
                  />
                  <span>{value}</span>
                </label>
              ))}
            </div>
          </fieldset>
          <button
            type="submit"
            disabled={busy}
            className="w-fit rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60"
          >
            {busy ? t("working") : t("saveProfile")}
          </button>
        </form>
      </section>

      <section className="flex flex-col gap-md">
        <h2 className="text-lg font-semibold text-ink">{t("addressesTitle")}</h2>
        {addresses.length === 0 ? (
          <p className="text-sm text-muted">{t("noAddresses")}</p>
        ) : (
          <ul className="flex flex-col gap-sm">
            {addresses.map((row) => (
              <li key={row.id} className="flex items-start justify-between gap-md text-sm">
                <div>
                  <p className="text-ink">
                    {row.line1}
                    {row.is_default ? ` · ${t("defaultAddress")}` : ""}
                  </p>
                  <p className="text-muted">
                    {[row.city, row.district, row.country].filter(Boolean).join(", ")}
                  </p>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onDeleteAddress(row.id)}
                  className="text-danger underline disabled:opacity-60"
                >
                  {t("delete")}
                </button>
              </li>
            ))}
          </ul>
        )}
        <form onSubmit={onAddAddress} className="flex flex-col gap-sm">
          <input
            required
            placeholder={t("line1")}
            value={line1}
            onChange={(e) => setLine1(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-sm text-ink"
          />
          <input
            required
            placeholder={t("city")}
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-sm text-ink"
          />
          <input
            placeholder={t("district")}
            value={district}
            onChange={(e) => setDistrict(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-sm text-ink"
          />
          <button
            type="submit"
            disabled={busy}
            className="w-fit rounded-sm border border-line px-md py-sm text-sm text-ink disabled:opacity-60"
          >
            {t("addAddress")}
          </button>
        </form>
      </section>

      <section className="flex flex-col gap-md">
        <h2 className="text-lg font-semibold text-ink">{t("sessionsTitle")}</h2>
        <ul className="flex flex-col gap-sm">
          {sessions.map((row) => (
            <li key={row.id} className="flex items-start justify-between gap-md text-sm">
              <div>
                <p className="text-ink">
                  {row.current ? t("thisDevice") : t("otherDevice")}
                  {row.ip ? ` · ${row.ip}` : ""}
                </p>
                <p className="text-muted">{row.user_agent || t("unknownAgent")}</p>
              </div>
              {!row.current ? (
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void onRevokeSession(row.id)}
                  className="text-danger underline disabled:opacity-60"
                >
                  {t("revoke")}
                </button>
              ) : null}
            </li>
          ))}
        </ul>
        <button
          type="button"
          disabled={busy}
          onClick={() => void onLogoutEverywhere()}
          className="w-fit rounded-sm border border-line px-md py-sm text-sm text-ink disabled:opacity-60"
        >
          {t("logoutEverywhere")}
        </button>
      </section>

      <section className="flex flex-col gap-md">
        <h2 className="text-lg font-semibold text-ink">{t("privacyTitle")}</h2>
        <p className="text-sm text-muted">{t("privacyHint")}</p>
        <div className="flex flex-wrap gap-sm">
          <button
            type="button"
            disabled={busy}
            onClick={() => void onExport()}
            className="rounded-sm border border-line px-md py-sm text-sm text-ink disabled:opacity-60"
          >
            {t("exportData")}
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void onDeleteAccount()}
            className="rounded-sm border border-danger px-md py-sm text-sm text-danger disabled:opacity-60"
          >
            {t("deleteAccount")}
          </button>
        </div>
      </section>
    </div>
  );
}

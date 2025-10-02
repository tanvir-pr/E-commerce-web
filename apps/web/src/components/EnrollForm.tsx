"use client";

import { FormEvent, useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

type Setup = { secret: string; otpauth_url: string; qr_svg: string };

export function EnrollForm() {
  const t = useTranslations("auth");
  const locale = useLocale();
  const router = useRouter();
  const [setup, setSetup] = useState<Setup | null>(null);
  const [code, setCode] = useState("");
  const [recovery, setRecovery] = useState<string[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const csrf = await fetchCsrfToken();
        const response = await apiPost("/api/v1/auth/totp/setup", {}, csrf);
        if (!active) {
          return;
        }
        if (!response.ok) {
          setError(await readProblem(response));
          return;
        }
        setSetup((await response.json()) as Setup);
      } catch {
        if (active) {
          setError(t("networkError"));
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [t]);

  async function onConfirm(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiPost("/api/v1/auth/totp/confirm", { code }, csrf);
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      const body = (await response.json()) as { recovery_codes: string[] };
      setRecovery(body.recovery_codes);
    } catch {
      setError(t("networkError"));
    } finally {
      setPending(false);
    }
  }

  if (recovery) {
    return (
      <div className="flex flex-col gap-md">
        <p className="text-sm text-ok">{t("enrollDone")}</p>
        <p className="text-sm text-muted">{t("recoveryHint")}</p>
        <ul className="grid grid-cols-2 gap-xs font-mono text-sm">
          {recovery.map((item) => (
            <li key={item} className="rounded-sm border border-line px-sm py-xs">
              {item}
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper"
          onClick={() => {
            router.push(`/${locale}/admin`);
            router.refresh();
          }}
        >
          {t("goAdmin")}
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-md">
      <p className="text-sm text-muted">{t("enrollHint")}</p>
      {setup ? (
        <>
          <div
            className="mx-auto w-fit rounded-sm border border-line bg-paper p-sm"
            dangerouslySetInnerHTML={{ __html: setup.qr_svg }}
          />
          <p className="break-all font-mono text-xs text-muted">{setup.secret}</p>
        </>
      ) : (
        <p className="text-sm text-muted">{t("working")}</p>
      )}
      <form onSubmit={onConfirm} className="flex flex-col gap-md">
        <label className="flex flex-col gap-xs text-sm">
          <span>{t("totpCode")}</span>
          <input
            inputMode="numeric"
            autoComplete="one-time-code"
            required
            minLength={6}
            maxLength={8}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
          />
        </label>
        {error ? (
          <p role="alert" className="text-sm text-danger">
            {error}
          </p>
        ) : null}
        <button
          type="submit"
          disabled={pending || !setup}
          className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60"
        >
          {pending ? t("working") : t("confirmTotp")}
        </button>
      </form>
    </div>
  );
}

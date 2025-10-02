"use client";

import { FormEvent, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export function ChallengeForm() {
  const t = useTranslations("auth");
  const locale = useLocale();
  const router = useRouter();
  const [code, setCode] = useState("");
  const [recoveryCode, setRecoveryCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const csrf = await fetchCsrfToken();
      const payload = recoveryCode.trim()
        ? { recovery_code: recoveryCode.trim() }
        : { code };
      const response = await apiPost("/api/v1/auth/totp/challenge", payload, csrf);
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      router.push(`/${locale}/admin`);
      router.refresh();
    } catch {
      setError(t("networkError"));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-col gap-md">
      <p className="text-sm text-muted">{t("challengeHint")}</p>
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("totpCode")}</span>
        <input
          inputMode="numeric"
          autoComplete="one-time-code"
          value={code}
          onChange={(e) => setCode(e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
        />
      </label>
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("recoveryCode")}</span>
        <input
          value={recoveryCode}
          onChange={(e) => setRecoveryCode(e.target.value)}
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
        disabled={pending || (!code && !recoveryCode.trim())}
        className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60"
      >
        {pending ? t("working") : t("verifyTotp")}
      </button>
    </form>
  );
}

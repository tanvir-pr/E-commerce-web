"use client";

import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";
import { z } from "zod";
import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

const schema = z.object({
  email: z.string().email(),
});

export function ForgotPasswordForm() {
  const t = useTranslations("account");
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const parsed = schema.safeParse({ email });
    if (!parsed.success) {
      setError(t("invalidEmail"));
      return;
    }
    setPending(true);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiPost("/api/v1/auth/password-reset/request", parsed.data, csrf);
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      setDone(true);
    } catch {
      setError(t("networkError"));
    } finally {
      setPending(false);
    }
  }

  if (done) {
    return <p className="text-sm text-ink">{t("resetSent")}</p>;
  }

  return (
    <form onSubmit={onSubmit} className="flex max-w-md flex-col gap-md">
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("email")}</span>
        <input
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
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
        disabled={pending}
        className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60"
      >
        {pending ? t("working") : t("sendReset")}
      </button>
    </form>
  );
}

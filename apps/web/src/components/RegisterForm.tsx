"use client";

import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";
import { z } from "zod";
import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(10),
});

export function RegisterForm() {
  const t = useTranslations("auth");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    const parsed = schema.safeParse({ email, password });
    if (!parsed.success) {
      setError(t("invalidForm"));
      return;
    }
    setPending(true);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiPost("/api/v1/auth/register", parsed.data, csrf);
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      const body = (await response.json()) as { message: string };
      setMessage(body.message || t("registerOk"));
      setPassword("");
    } catch {
      setError(t("networkError"));
    } finally {
      setPending(false);
    }
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
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("password")}</span>
        <input
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
        />
      </label>
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
      <button
        type="submit"
        disabled={pending}
        className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60"
      >
        {pending ? t("working") : t("registerSubmit")}
      </button>
    </form>
  );
}

"use client";

import { FormEvent, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

const schema = z.object({
  password: z.string().min(10).max(128),
});

export function ResetPasswordForm({ token }: { token: string | null }) {
  const t = useTranslations("account");
  const locale = useLocale();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  if (!token) {
    return <p className="text-sm text-danger">{t("missingResetToken")}</p>;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    const parsed = schema.safeParse({ password });
    if (!parsed.success) {
      setError(t("invalidPassword"));
      return;
    }
    setPending(true);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiPost(
        "/api/v1/auth/password-reset/confirm",
        { token, password: parsed.data.password },
        csrf,
      );
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      router.push(`/${locale}/login`);
      router.refresh();
    } catch {
      setError(t("networkError"));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex max-w-md flex-col gap-md">
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("newPassword")}</span>
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
      <button
        type="submit"
        disabled={pending}
        className="rounded-sm bg-ink px-md py-sm text-sm font-medium text-paper disabled:opacity-60"
      >
        {pending ? t("working") : t("savePassword")}
      </button>
    </form>
  );
}

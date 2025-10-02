"use client";

import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";
import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

const PERMS = ["support", "warehouse", "moderation"] as const;

export function StaffCreateForm() {
  const t = useTranslations("admin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [perms, setPerms] = useState<string[]>([]);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  function toggle(perm: string) {
    setPerms((current) =>
      current.includes(perm) ? current.filter((p) => p !== perm) : [...current, perm],
    );
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setPending(true);
    try {
      const csrf = await fetchCsrfToken();
      const response = await apiPost(
        "/api/v1/admin/staff",
        { email, password, permissions: perms },
        csrf,
      );
      if (!response.ok) {
        setError(await readProblem(response));
        return;
      }
      const body = (await response.json()) as { id: string };
      setMessage(t("staffCreated", { id: body.id }));
      setEmail("");
      setPassword("");
      setPerms([]);
    } catch {
      setError(t("networkError"));
    } finally {
      setPending(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="flex max-w-md flex-col gap-md">
      <p className="text-sm text-muted">{t("staffHint")}</p>
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("staffEmail")}</span>
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
        />
      </label>
      <label className="flex flex-col gap-xs text-sm">
        <span>{t("staffPassword")}</span>
        <input
          type="password"
          required
          minLength={10}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-sm border border-line bg-surface px-sm py-sm text-ink"
        />
      </label>
      <fieldset className="flex flex-col gap-xs text-sm">
        <legend>{t("staffPermissions")}</legend>
        {PERMS.map((perm) => (
          <label key={perm} className="flex items-center gap-sm">
            <input
              type="checkbox"
              checked={perms.includes(perm)}
              onChange={() => toggle(perm)}
            />
            <span>{perm}</span>
          </label>
        ))}
      </fieldset>
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
        {pending ? t("working") : t("createStaff")}
      </button>
    </form>
  );
}

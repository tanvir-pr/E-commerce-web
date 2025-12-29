"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  fetchAdminFeatureFlags,
  patchFeatureFlag,
  type FeatureFlag,
} from "@/lib/flags";

export function AdminFeatureFlags() {
  const t = useTranslations("adminFlags");
  const [items, setItems] = useState<FeatureFlag[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setItems(await fetchAdminFeatureFlags());
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

  async function toggle(flag: FeatureFlag) {
    setPending(true);
    setError(null);
    try {
      const updated = await patchFeatureFlag(flag.id, { enabled: !flag.enabled });
      setItems((rows) => rows.map((row) => (row.id === updated.id ? updated : row)));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-md">
      <p className="text-sm text-muted">{t("hint")}</p>
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {items.length === 0 ? (
        <p className="text-sm text-muted">{t("empty")}</p>
      ) : (
        <ul className="divide-y divide-line border-t border-line">
          {items.map((flag) => (
            <li key={flag.id} className="flex flex-wrap items-start justify-between gap-md py-md">
              <div className="min-w-0 flex-1">
                <p className="font-mono text-sm text-ink">{flag.key}</p>
                {flag.description ? (
                  <p className="mt-2xs text-sm text-muted">{flag.description}</p>
                ) : null}
                {flag.value ? (
                  <pre className="mt-2xs overflow-x-auto text-xs text-muted">
                    {JSON.stringify(flag.value)}
                  </pre>
                ) : null}
              </div>
              <button
                type="button"
                disabled={pending}
                onClick={() => void toggle(flag)}
                className={
                  flag.enabled
                    ? "rounded-sm bg-sage px-md py-2xs text-sm text-white disabled:opacity-60"
                    : "rounded-sm border border-line px-md py-2xs text-sm text-muted disabled:opacity-60"
                }
              >
                {flag.enabled ? t("on") : t("off")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

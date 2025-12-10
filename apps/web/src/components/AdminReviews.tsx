"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { fetchAdminReviews, moderateReview, type Review } from "@/lib/reviews";

export function AdminReviews() {
  const t = useTranslations("adminReviews");
  const [items, setItems] = useState<Review[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setItems(await fetchAdminReviews());
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

  async function onToggle(row: Review) {
    setPending(true);
    setError(null);
    try {
      await moderateReview(row.id, !row.is_published);
      await load();
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
      <button type="button" onClick={() => void load()} className="w-fit text-sm text-sage underline">
        {t("refresh")}
      </button>
      {items.length === 0 ? (
        <p className="text-sm text-muted">{t("empty")}</p>
      ) : (
        <ul className="divide-y divide-line border-t border-line text-sm">
          {items.map((row) => (
            <li
              key={row.id}
              className="flex flex-col gap-sm py-md md:flex-row md:items-center md:justify-between"
            >
              <div>
                <p className="font-medium text-ink">
                  {row.product_name ?? row.product_id} · {"★".repeat(row.rating)}
                  {!row.is_published ? (
                    <span className="ml-xs text-danger">· {t("hidden")}</span>
                  ) : null}
                  {row.is_verified ? (
                    <span className="ml-xs text-sage">· {t("verified")}</span>
                  ) : null}
                </p>
                <p className="text-muted">{row.body}</p>
                <p className="text-xs text-muted">
                  {row.author_display}
                  {row.skin_type ? ` · ${row.skin_type}` : ""}
                </p>
              </div>
              <button
                type="button"
                disabled={pending}
                onClick={() => void onToggle(row)}
                className="rounded-sm border border-line px-sm py-2xs text-xs disabled:opacity-60"
              >
                {row.is_published ? t("hide") : t("publish")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

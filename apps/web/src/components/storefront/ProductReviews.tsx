"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { fetchMe } from "@/lib/api";
import {
  createProductReview,
  fetchProductReviews,
  type Review,
  type ReviewList,
} from "@/lib/reviews";

export function ProductReviews({
  slug,
  locale,
  initialAvg,
  initialCount,
}: {
  slug: string;
  locale: string;
  initialAvg: number | null;
  initialCount: number;
}) {
  const t = useTranslations("reviews");
  const [data, setData] = useState<ReviewList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [signedIn, setSignedIn] = useState(false);
  const [rating, setRating] = useState(5);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setData(await fetchProductReviews(slug));
  }, [slug]);

  useEffect(() => {
    let active = true;
    void (async () => {
      try {
        const me = await fetchMe();
        if (!active) {
          return;
        }
        setSignedIn(Boolean(me));
        await load();
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : t("loadFailed"));
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [load, t]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    try {
      await createProductReview(slug, {
        rating,
        title: title.trim() || undefined,
        body: body.trim(),
      });
      setTitle("");
      setBody("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  const avg = data?.rating_avg ?? initialAvg;
  const count = data?.rating_count ?? initialCount;
  const items: Review[] = data?.items ?? [];

  return (
    <section className="mt-3xl border-t border-line pt-xl">
      <h2 className="font-display text-2xl text-ink">{t("title")}</h2>
      <p className="mt-sm text-sm text-muted">
        {count > 0
          ? t("summary", { avg: avg?.toFixed(1) ?? "—", count })
          : t("empty")}
      </p>
      {error ? (
        <p role="alert" className="mt-sm text-sm text-danger">
          {error}
        </p>
      ) : null}

      {items.length > 0 ? (
        <ul className="mt-md divide-y divide-line border-t border-line">
          {items.map((row) => (
            <li key={row.id} className="py-md">
              <p className="text-sm font-medium text-ink">
                {"★".repeat(row.rating)}
                {"☆".repeat(5 - row.rating)}
                {row.is_verified ? (
                  <span className="ml-sm text-xs text-sage">{t("verified")}</span>
                ) : null}
              </p>
              {row.title ? (
                <p className="mt-2xs text-sm font-medium text-ink">{row.title}</p>
              ) : null}
              <p className="mt-2xs text-sm text-muted">{row.body}</p>
              <p className="mt-2xs text-xs text-muted">
                {row.author_display ?? t("anonymous")}
                {row.skin_type ? ` · ${t("skinType", { type: row.skin_type })}` : ""}
              </p>
            </li>
          ))}
        </ul>
      ) : null}

      {data?.can_review ? (
        <form onSubmit={(e) => void onSubmit(e)} className="mt-lg flex max-w-lg flex-col gap-sm">
          <h3 className="text-sm font-semibold text-ink">{t("writeTitle")}</h3>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("rating")}</span>
            <select
              value={rating}
              onChange={(e) => setRating(Number.parseInt(e.target.value, 10))}
              className="rounded-sm border border-line px-sm py-2xs"
            >
              {[5, 4, 3, 2, 1].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("reviewTitle")}</span>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="rounded-sm border border-line px-sm py-2xs"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("body")}</span>
            <textarea
              required
              minLength={8}
              rows={4}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="rounded-sm border border-line px-sm py-2xs"
            />
          </label>
          <button
            type="submit"
            disabled={pending}
            className="w-fit rounded-sm bg-sage px-md py-sm text-sm text-white disabled:opacity-60"
          >
            {pending ? t("working") : t("submit")}
          </button>
        </form>
      ) : signedIn ? (
        <p className="mt-md text-sm text-muted">{t("needPurchase")}</p>
      ) : (
        <p className="mt-md text-sm text-muted">
          <Link href={`/${locale}/login`} className="underline">
            {t("signInToReview")}
          </Link>
        </p>
      )}
    </section>
  );
}

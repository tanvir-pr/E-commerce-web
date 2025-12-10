"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { fetchMe } from "@/lib/api";
import { formatBdt } from "@/lib/catalog";
import { fetchWishlist, removeFromWishlist, type WishlistItem } from "@/lib/wishlist";

export function WishlistPanel() {
  const t = useTranslations("wishlist");
  const locale = useLocale();
  const [items, setItems] = useState<WishlistItem[] | null>(null);
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setItems(await fetchWishlist());
  }, []);

  useEffect(() => {
    let active = true;
    void (async () => {
      const me = await fetchMe();
      if (!active) {
        return;
      }
      setSignedIn(Boolean(me));
      if (!me) {
        setItems([]);
        return;
      }
      try {
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

  async function onRemove(productId: string) {
    setPending(true);
    setError(null);
    try {
      await removeFromWishlist(productId);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  if (signedIn === null || items === null) {
    return <p className="text-sm text-muted">{t("loading")}</p>;
  }

  if (!signedIn) {
    return (
      <p className="text-sm text-muted">
        <Link href={`/${locale}/login`} className="underline">
          {t("signIn")}
        </Link>
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-md">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {items.length === 0 ? (
        <p className="text-sm text-muted">{t("empty")}</p>
      ) : (
        <ul className="divide-y divide-line border-t border-line">
          {items.map((row) => (
            <li
              key={row.id}
              className="flex flex-col gap-sm py-md md:flex-row md:items-center md:justify-between"
            >
              <div>
                <Link
                  href={`/${locale}/p/${row.product_slug}`}
                  className="font-medium text-ink underline"
                >
                  {row.product_name}
                </Link>
                {row.subtitle ? (
                  <p className="text-sm text-muted">{row.subtitle}</p>
                ) : null}
                <p className="text-sm text-muted">{formatBdt(row.from_price_poisha)}</p>
              </div>
              <button
                type="button"
                disabled={pending}
                onClick={() => void onRemove(row.product_id)}
                className="w-fit text-sm text-danger underline disabled:opacity-60"
              >
                {t("remove")}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

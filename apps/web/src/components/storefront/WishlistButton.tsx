"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { fetchMe } from "@/lib/api";
import { addToWishlist, fetchWishlist, removeFromWishlist } from "@/lib/wishlist";

export function WishlistButton({
  productId,
  locale,
}: {
  productId: string;
  locale: string;
}) {
  const t = useTranslations("wishlist");
  const [signedIn, setSignedIn] = useState<boolean | null>(null);
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      const me = await fetchMe();
      if (!active) {
        return;
      }
      setSignedIn(Boolean(me));
      if (!me) {
        return;
      }
      try {
        const items = await fetchWishlist();
        if (active) {
          setSaved(items.some((i) => i.product_id === productId));
        }
      } catch {
        /* ignore */
      }
    })();
    return () => {
      active = false;
    };
  }, [productId]);

  if (signedIn === null) {
    return null;
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

  async function toggle() {
    setPending(true);
    setError(null);
    try {
      if (saved) {
        await removeFromWishlist(productId);
        setSaved(false);
      } else {
        await addToWishlist(productId);
        setSaved(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-2xs">
      <button
        type="button"
        disabled={pending}
        onClick={() => void toggle()}
        className="w-fit rounded-sm border border-line px-md py-sm text-sm text-ink hover:border-sage disabled:opacity-60"
      >
        {pending ? t("working") : saved ? t("remove") : t("add")}
      </button>
      {error ? (
        <p role="alert" className="text-xs text-danger">
          {error}
        </p>
      ) : null}
    </div>
  );
}

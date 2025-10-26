"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

/** Part 11 ships the press micro-motion; cart wiring lands in Part 13. */
export function AddToBagButton({ disabled }: { disabled?: boolean }) {
  const t = useTranslations("storefront");
  const [note, setNote] = useState<string | null>(null);
  const [pop, setPop] = useState(false);

  function onClick() {
    setPop(true);
    setNote(t("cartSoon"));
    window.setTimeout(() => setPop(false), 320);
  }

  return (
    <div className="flex flex-col gap-xs">
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        className={`btn-press rounded-sm bg-saffron px-lg py-sm text-sm font-medium text-ink disabled:opacity-50 ${
          pop ? "animate-press-pop" : ""
        }`}
      >
        {t("addToBag")}
      </button>
      {note ? (
        <p role="status" className="text-xs text-muted">
          {note}
        </p>
      ) : null}
    </div>
  );
}

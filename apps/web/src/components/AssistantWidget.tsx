"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  askAssistant,
  fetchAssistantStatus,
  handoffAssistant,
  type AssistantAskResult,
} from "@/lib/assistant";
import { formatBdt } from "@/lib/catalog";

type ChatLine = {
  role: "user" | "assistant";
  content: string;
  products?: AssistantAskResult["products"];
  citations?: AssistantAskResult["citations"];
  handoff?: boolean;
};

export function AssistantWidget() {
  const t = useTranslations("assistant");
  const locale = useLocale();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [enabled, setEnabled] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [lines, setLines] = useState<ChatLine[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [handoffDone, setHandoffDone] = useState(false);

  const onAdmin = pathname.includes("/admin");

  useEffect(() => {
    if (onAdmin) {
      return;
    }
    let active = true;
    void (async () => {
      try {
        const status = await fetchAssistantStatus();
        if (active) {
          setEnabled(status.enabled);
        }
      } catch {
        if (active) {
          setEnabled(false);
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [onAdmin]);

  if (onAdmin || !enabled) {
    return null;
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || pending) {
      return;
    }
    setPending(true);
    setError(null);
    setInput("");
    setLines((prev) => [...prev, { role: "user", content: message }]);
    try {
      const result = await askAssistant({
        message,
        conversation_id: conversationId,
        locale,
      });
      setConversationId(result.conversation_id);
      setLines((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.reply,
          products: result.products,
          citations: result.citations,
          handoff: result.handoff_suggested,
        },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("askFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onHandoff() {
    if (!conversationId || pending) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      await handoffAssistant({ conversation_id: conversationId });
      setHandoffDone(true);
      setLines((prev) => [
        ...prev,
        { role: "assistant", content: t("handoffOk") },
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : t("handoffFailed");
      if (msg.toLowerCase().includes("sign in") || msg.toLowerCase().includes("unauthorized")) {
        setError(t("signInForHandoff"));
      } else {
        setError(msg);
      }
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="fixed bottom-md right-md z-30 flex flex-col items-end gap-sm">
      {open ? (
        <div className="flex h-[min(28rem,70vh)] w-[min(22rem,calc(100vw-2rem))] flex-col border border-line bg-paper shadow-lg">
          <div className="flex items-center justify-between border-b border-line px-md py-sm">
            <div>
              <p className="text-sm font-semibold text-ink">{t("title")}</p>
              <p className="text-xs text-muted">{t("subtitle")}</p>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="text-sm text-muted hover:text-ink"
              aria-label={t("close")}
            >
              ×
            </button>
          </div>
          <div className="flex-1 space-y-sm overflow-y-auto px-md py-sm text-sm">
            {lines.length === 0 ? (
              <p className="text-muted">{t("welcome")}</p>
            ) : null}
            {lines.map((line, index) => (
              <div
                key={`${line.role}-${index}`}
                className={line.role === "user" ? "text-right" : "text-left"}
              >
                <p
                  className={
                    line.role === "user"
                      ? "inline-block bg-ink px-sm py-2xs text-left text-paper"
                      : "whitespace-pre-wrap text-ink"
                  }
                >
                  {line.content}
                </p>
                {line.products && line.products.length > 0 ? (
                  <ul className="mt-2xs space-y-2xs">
                    {line.products.map((product) => (
                      <li key={product.id}>
                        <Link
                          href={`/${locale}/p/${product.slug}`}
                          className="text-sage underline"
                        >
                          {product.name}
                          {product.from_price_poisha != null
                            ? ` · ${formatBdt(product.from_price_poisha)}`
                            : ""}
                          {product.in_stock ? "" : ` · ${t("outOfStock")}`}
                        </Link>
                      </li>
                    ))}
                  </ul>
                ) : null}
                {line.citations && line.citations.length > 0 ? (
                  <p className="mt-2xs text-xs text-muted">
                    {t("sources")}: {line.citations.map((c) => c.title).join(" · ")}
                  </p>
                ) : null}
                {line.handoff && !handoffDone ? (
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => void onHandoff()}
                    className="mt-2xs text-xs text-sage underline disabled:opacity-60"
                  >
                    {t("handoff")}
                  </button>
                ) : null}
              </div>
            ))}
            {error ? (
              <p role="alert" className="text-sm text-danger">
                {error}
              </p>
            ) : null}
          </div>
          <form
            onSubmit={(e) => void onSubmit(e)}
            className="flex gap-2xs border-t border-line p-sm"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={t("placeholder")}
              className="min-w-0 flex-1 border border-line bg-surface px-sm py-2xs text-sm"
              disabled={pending || handoffDone}
              maxLength={2000}
            />
            <button
              type="submit"
              disabled={pending || handoffDone || !input.trim()}
              className="bg-sage px-sm py-2xs text-sm text-white disabled:opacity-60"
            >
              {pending ? t("sending") : t("send")}
            </button>
          </form>
        </div>
      ) : null}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="bg-ink px-md py-sm text-sm text-paper shadow-md"
        aria-expanded={open}
      >
        {open ? t("close") : t("open")}
      </button>
    </div>
  );
}

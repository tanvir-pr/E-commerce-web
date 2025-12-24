"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  fetchAdminTicket,
  fetchAdminTickets,
  replyAdminTicket,
  setAdminTicketStatus,
  type Ticket,
  type TicketSummary,
} from "@/lib/support";

export function AdminSupport() {
  const t = useTranslations("adminSupport");
  const [status, setStatus] = useState("open");
  const [items, setItems] = useState<TicketSummary[]>([]);
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [reply, setReply] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    setItems(await fetchAdminTickets(status));
  }, [status]);

  useEffect(() => {
    void (async () => {
      try {
        await load();
      } catch (err) {
        setError(err instanceof Error ? err.message : t("loadFailed"));
      }
    })();
  }, [load, t]);

  async function openTicket(id: string) {
    setPending(true);
    setError(null);
    try {
      setSelected(await fetchAdminTicket(id));
      setReply("");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loadFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onReply(event: FormEvent) {
    event.preventDefault();
    if (!selected) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      const updated = await replyAdminTicket(selected.id, reply.trim());
      setSelected(updated);
      setReply("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onClose() {
    if (!selected) {
      return;
    }
    setPending(true);
    setError(null);
    try {
      const updated = await setAdminTicketStatus(selected.id, "closed");
      setSelected(updated);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-lg">
      <p className="text-sm text-muted">{t("hint")}</p>
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      <div className="flex flex-wrap gap-sm text-sm">
        {(["open", "pending", "closed", "all"] as const).map((key) => (
          <button
            key={key}
            type="button"
            onClick={() => setStatus(key)}
            className={
              status === key
                ? "rounded-sm bg-ink px-sm py-2xs text-paper"
                : "rounded-sm border border-line px-sm py-2xs text-ink"
            }
          >
            {t(`filter.${key}`)}
          </button>
        ))}
        <button type="button" onClick={() => void load()} className="text-sage underline">
          {t("refresh")}
        </button>
      </div>

      <div className="grid gap-lg md:grid-cols-2">
        <ul className="divide-y divide-line border-t border-line text-sm">
          {items.length === 0 ? (
            <li className="py-md text-muted">{t("empty")}</li>
          ) : (
            items.map((row) => (
              <li key={row.id}>
                <button
                  type="button"
                  onClick={() => void openTicket(row.id)}
                  className="flex w-full flex-col items-start gap-2xs py-md text-left hover:bg-sage-soft/30"
                >
                  <span className="font-medium text-ink">
                    {row.subject} · {row.status}
                  </span>
                  <span className="text-muted">
                    {row.topic} · {row.user_email ?? "—"} · {row.message_count}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>

        <div className="border-t border-line pt-md md:border-t-0 md:border-l md:pl-lg md:pt-0">
          {!selected ? (
            <p className="text-sm text-muted">{t("pick")}</p>
          ) : (
            <div className="flex flex-col gap-md">
              <div>
                <h2 className="font-medium text-ink">{selected.subject}</h2>
                <p className="text-sm text-muted">
                  {selected.topic} · {selected.status} · {selected.user_email}
                </p>
              </div>
              <ul className="flex flex-col gap-sm text-sm">
                {selected.messages.map((m) => (
                  <li
                    key={m.id}
                    className={
                      m.is_staff
                        ? "border-l-2 border-sage pl-sm text-ink"
                        : "border-l-2 border-line pl-sm text-muted"
                    }
                  >
                    <p>{m.body}</p>
                    <p className="text-xs">
                      {m.is_staff ? t("staff") : t("customer")} ·{" "}
                      {new Date(m.created_at).toLocaleString()}
                    </p>
                  </li>
                ))}
              </ul>
              {selected.status !== "closed" ? (
                <form onSubmit={(e) => void onReply(e)} className="flex flex-col gap-sm">
                  <textarea
                    required
                    rows={3}
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    className="rounded-sm border border-line px-sm py-2xs text-sm"
                    placeholder={t("replyPlaceholder")}
                  />
                  <div className="flex gap-sm">
                    <button
                      type="submit"
                      disabled={pending}
                      className="rounded-sm bg-sage px-md py-sm text-sm text-white disabled:opacity-60"
                    >
                      {pending ? t("working") : t("reply")}
                    </button>
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => void onClose()}
                      className="rounded-sm border border-line px-md py-sm text-sm disabled:opacity-60"
                    >
                      {t("close")}
                    </button>
                  </div>
                </form>
              ) : null}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

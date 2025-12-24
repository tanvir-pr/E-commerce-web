"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  createTicket,
  fetchMyTicket,
  fetchMyTickets,
  fetchNotificationPrefs,
  patchNotificationPrefs,
  replyMyTicket,
  type NotificationPrefs,
  type Ticket,
  type TicketSummary,
} from "@/lib/support";

export function SupportAccountSection() {
  const t = useTranslations("support");
  const [prefs, setPrefs] = useState<NotificationPrefs | null>(null);
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [topic, setTopic] = useState<"order" | "product" | "account" | "other">("account");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [reply, setReply] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const load = useCallback(async () => {
    const [p, list] = await Promise.all([fetchNotificationPrefs(), fetchMyTickets()]);
    setPrefs(p);
    setTickets(list);
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

  async function onSavePrefs(event: FormEvent) {
    event.preventDefault();
    if (!prefs) {
      return;
    }
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      setPrefs(await patchNotificationPrefs(prefs));
      setMessage(t("prefsSaved"));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function onCreateTicket(event: FormEvent) {
    event.preventDefault();
    setPending(true);
    setError(null);
    setMessage(null);
    try {
      const created = await createTicket({
        topic,
        subject: subject.trim(),
        body: body.trim(),
      });
      setSubject("");
      setBody("");
      setSelected(created);
      setMessage(t("ticketCreated"));
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  async function openTicket(id: string) {
    setPending(true);
    setError(null);
    try {
      setSelected(await fetchMyTicket(id));
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
      setSelected(await replyMyTicket(selected.id, reply.trim()));
      setReply("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("saveFailed"));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col gap-xl">
      {error ? (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      ) : null}
      {message ? <p className="text-sm text-ok">{message}</p> : null}

      <section className="flex flex-col gap-md">
        <h2 className="text-lg font-semibold text-ink">{t("prefsTitle")}</h2>
        <p className="text-sm text-muted">{t("prefsHint")}</p>
        {prefs ? (
          <form onSubmit={(e) => void onSavePrefs(e)} className="flex flex-col gap-sm text-sm">
            {(
              [
                ["order_updates", "orderUpdates"],
                ["marketing", "marketing"],
                ["stock_back", "stockBack"],
                ["support_replies", "supportReplies"],
              ] as const
            ).map(([key, labelKey]) => (
              <label key={key} className="flex items-center gap-sm text-muted">
                <input
                  type="checkbox"
                  checked={prefs[key]}
                  onChange={(e) => setPrefs({ ...prefs, [key]: e.target.checked })}
                />
                {t(labelKey)}
              </label>
            ))}
            <button
              type="submit"
              disabled={pending}
              className="mt-sm w-fit rounded-sm bg-ink px-md py-sm text-paper disabled:opacity-60"
            >
              {pending ? t("working") : t("savePrefs")}
            </button>
          </form>
        ) : (
          <p className="text-sm text-muted">{t("loading")}</p>
        )}
      </section>

      <section className="flex flex-col gap-md">
        <h2 className="text-lg font-semibold text-ink">{t("ticketsTitle")}</h2>
        <form onSubmit={(e) => void onCreateTicket(e)} className="flex max-w-lg flex-col gap-sm">
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("topic")}</span>
            <select
              value={topic}
              onChange={(e) =>
                setTopic(e.target.value as "order" | "product" | "account" | "other")
              }
              className="rounded-sm border border-line px-sm py-2xs"
            >
              <option value="order">{t("topicOrder")}</option>
              <option value="product">{t("topicProduct")}</option>
              <option value="account">{t("topicAccount")}</option>
              <option value="other">{t("topicOther")}</option>
            </select>
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("subject")}</span>
            <input
              required
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="rounded-sm border border-line px-sm py-2xs"
            />
          </label>
          <label className="flex flex-col gap-2xs text-sm">
            <span className="text-muted">{t("body")}</span>
            <textarea
              required
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
            {pending ? t("working") : t("createTicket")}
          </button>
        </form>

        <ul className="divide-y divide-line border-t border-line text-sm">
          {tickets.length === 0 ? (
            <li className="py-md text-muted">{t("noTickets")}</li>
          ) : (
            tickets.map((row) => (
              <li key={row.id}>
                <button
                  type="button"
                  onClick={() => void openTicket(row.id)}
                  className="flex w-full flex-col items-start gap-2xs py-md text-left"
                >
                  <span className="font-medium text-ink">
                    {row.subject} · {row.status}
                  </span>
                  <span className="text-muted">
                    {row.topic} · {new Date(row.updated_at).toLocaleString()}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>

        {selected ? (
          <div className="flex flex-col gap-sm border-t border-line pt-md">
            <h3 className="font-medium text-ink">{selected.subject}</h3>
            <ul className="flex flex-col gap-sm text-sm">
              {selected.messages.map((m) => (
                <li
                  key={m.id}
                  className={
                    m.is_staff
                      ? "border-l-2 border-sage pl-sm"
                      : "border-l-2 border-line pl-sm text-muted"
                  }
                >
                  <p>{m.body}</p>
                  <p className="text-xs">
                    {m.is_staff ? t("staff") : t("you")} ·{" "}
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
                />
                <button
                  type="submit"
                  disabled={pending}
                  className="w-fit rounded-sm border border-line px-md py-sm text-sm disabled:opacity-60"
                >
                  {pending ? t("working") : t("reply")}
                </button>
              </form>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}

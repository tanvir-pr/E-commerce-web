import { apiPatch, apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export type NotificationPrefs = {
  order_updates: boolean;
  marketing: boolean;
  stock_back: boolean;
  support_replies: boolean;
};

export type TicketMessage = {
  id: string;
  body: string;
  is_staff: boolean;
  author_user_id: string | null;
  created_at: string;
};

export type TicketSummary = {
  id: string;
  topic: string;
  subject: string;
  status: string;
  order_id: string | null;
  product_id: string | null;
  created_at: string;
  updated_at: string;
  user_email?: string | null;
  message_count: number;
};

export type Ticket = TicketSummary & {
  messages: TicketMessage[];
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchNotificationPrefs(): Promise<NotificationPrefs> {
  const response = await fetch("/api/v1/users/me/notification-preferences", {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function patchNotificationPrefs(
  body: Partial<NotificationPrefs>,
): Promise<NotificationPrefs> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPatch("/api/v1/users/me/notification-preferences", body, csrf));
}

export async function fetchMyTickets(): Promise<TicketSummary[]> {
  const response = await fetch("/api/v1/support/tickets", {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: TicketSummary[] }>(response);
  return body.items;
}

export async function fetchMyTicket(id: string): Promise<Ticket> {
  const response = await fetch(`/api/v1/support/tickets/${id}`, {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function createTicket(body: {
  topic: "order" | "product" | "account" | "other";
  subject: string;
  body: string;
  order_id?: string;
  product_id?: string;
}): Promise<Ticket> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/support/tickets", body, csrf));
}

export async function replyMyTicket(id: string, body: string): Promise<Ticket> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost(`/api/v1/support/tickets/${id}/messages`, { body }, csrf));
}

export async function fetchAdminTickets(status = "open"): Promise<TicketSummary[]> {
  const response = await fetch(`/api/v1/admin/support/tickets?status=${status}`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: TicketSummary[] }>(response);
  return body.items;
}

export async function fetchAdminTicket(id: string): Promise<Ticket> {
  const response = await fetch(`/api/v1/admin/support/tickets/${id}`, {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function replyAdminTicket(id: string, body: string): Promise<Ticket> {
  const csrf = await fetchCsrfToken();
  return okJson(
    await apiPost(`/api/v1/admin/support/tickets/${id}/messages`, { body }, csrf),
  );
}

export async function setAdminTicketStatus(
  id: string,
  status: "open" | "pending" | "closed",
): Promise<Ticket> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPatch(`/api/v1/admin/support/tickets/${id}`, { status }, csrf));
}

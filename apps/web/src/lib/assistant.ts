import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export type AssistantCitation = {
  source: string;
  title: string;
  excerpt: string;
};

export type AssistantProductCard = {
  id: string;
  slug: string;
  name: string;
  subtitle: string | null;
  from_price_poisha: number | null;
  qty_available: number | null;
  in_stock: boolean;
  routine_step: string | null;
  concerns: string[];
  ingredients: string[];
};

export type AssistantAskResult = {
  conversation_id: string;
  message_id: string;
  reply: string;
  intent: string;
  confidence: number;
  handoff_suggested: boolean;
  citations: AssistantCitation[];
  products: AssistantProductCard[];
};

export type AssistantStatus = {
  enabled: boolean;
};

export type AssistantHandoffResult = {
  conversation_id: string;
  ticket_id: string;
  message: string;
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchAssistantStatus(): Promise<AssistantStatus> {
  const response = await fetch("/api/v1/assistant/status", {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function askAssistant(payload: {
  message: string;
  conversation_id?: string | null;
  locale?: string;
}): Promise<AssistantAskResult> {
  const csrf = await fetchCsrfToken();
  return okJson(
    await apiPost(
      "/api/v1/assistant/ask",
      {
        message: payload.message,
        conversation_id: payload.conversation_id || null,
        locale: payload.locale || "en",
      },
      csrf,
    ),
  );
}

export async function handoffAssistant(payload: {
  conversation_id: string;
  note?: string;
}): Promise<AssistantHandoffResult> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPost("/api/v1/assistant/handoff", payload, csrf));
}

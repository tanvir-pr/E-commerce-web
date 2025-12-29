import { apiPatch, fetchCsrfToken, readProblem } from "@/lib/api";

export type CheckoutMethods = {
  checkout_enabled: boolean;
  methods: string[];
  cod_fraud_check_enabled: boolean;
};

export type FeatureFlag = {
  id: string;
  key: string;
  enabled: boolean;
  value: Record<string, unknown> | null;
  description: string | null;
  updated_at: string;
};

async function okJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error(await readProblem(response));
  }
  return (await response.json()) as T;
}

export async function fetchCheckoutMethods(): Promise<CheckoutMethods> {
  const response = await fetch("/api/v1/checkout/methods", {
    credentials: "include",
    cache: "no-store",
  });
  return okJson(response);
}

export async function fetchAdminFeatureFlags(): Promise<FeatureFlag[]> {
  const response = await fetch("/api/v1/admin/feature-flags", {
    credentials: "include",
    cache: "no-store",
  });
  const body = await okJson<{ items: FeatureFlag[] }>(response);
  return body.items;
}

export async function patchFeatureFlag(
  id: string,
  payload: { enabled?: boolean; value?: Record<string, unknown> | null; description?: string | null },
): Promise<FeatureFlag> {
  const csrf = await fetchCsrfToken();
  return okJson(await apiPatch(`/api/v1/admin/feature-flags/${id}`, payload, csrf));
}

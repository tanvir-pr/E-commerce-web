export type Health = {
  status: "ok" | "down";
  db: "ok" | "down";
  redis: "ok" | "down";
  search?: "ok" | "down" | "disabled";
};

export type Me = {
  id: string;
  email: string;
  display_name: string | null;
  email_verified_at: string | null;
  phone: string | null;
  phone_verified_at: string | null;
  roles: string[];
  permissions: string[];
  totp_enabled: boolean;
  skin_type: string | null;
  skin_concerns: string[];
};

export type Address = {
  id: string;
  label: string | null;
  line1: string;
  line2: string | null;
  city: string;
  district: string | null;
  postal_code: string | null;
  country: string;
  phone: string | null;
  is_default: boolean;
};

export type Session = {
  id: string;
  family_id: string;
  created_at: string;
  expires_at: string;
  ip: string | null;
  user_agent: string | null;
  current: boolean;
};

export type AuthConfig = {
  phone_registration_enabled: boolean;
  skin_types: string[];
  skin_concerns: string[];
};

export async function fetchHealth(): Promise<Health | null> {
  try {
    const response = await fetch("/api/v1/health", { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    const body = (await response.json()) as Health;
    return body.status === "ok" ? body : null;
  } catch {
    return null;
  }
}

export async function fetchCsrfToken(): Promise<string> {
  const response = await fetch("/api/v1/auth/csrf", {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("csrf");
  }
  const body = (await response.json()) as { csrf_token?: string };
  if (!body.csrf_token) {
    throw new Error("csrf");
  }
  return body.csrf_token;
}

export async function apiSend(
  method: string,
  path: string,
  payload: unknown,
  csrf: string,
): Promise<Response> {
  return fetch(path, {
    method,
    credentials: "include",
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
    },
    body: payload === undefined ? undefined : JSON.stringify(payload),
    cache: "no-store",
  });
}

export async function apiPost(path: string, payload: unknown, csrf: string): Promise<Response> {
  return apiSend("POST", path, payload, csrf);
}

export async function apiPut(path: string, payload: unknown, csrf: string): Promise<Response> {
  return apiSend("PUT", path, payload, csrf);
}

export async function apiPatch(path: string, payload: unknown, csrf: string): Promise<Response> {
  return apiSend("PATCH", path, payload, csrf);
}

export async function apiDelete(path: string, csrf: string): Promise<Response> {
  return fetch(path, {
    method: "DELETE",
    credentials: "include",
    headers: {
      Accept: "application/json",
      "X-CSRF-Token": csrf,
    },
    cache: "no-store",
  });
}

export async function fetchMe(): Promise<Me | null> {
  try {
    const response = await fetch("/api/v1/users/me", {
      credentials: "include",
      cache: "no-store",
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as Me;
  } catch {
    return null;
  }
}

export async function fetchAuthConfig(): Promise<AuthConfig | null> {
  try {
    const response = await fetch("/api/v1/auth/config", { cache: "no-store" });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as AuthConfig;
  } catch {
    return null;
  }
}

export async function fetchAddresses(): Promise<Address[]> {
  const response = await fetch("/api/v1/users/me/addresses", {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("addresses");
  }
  return (await response.json()) as Address[];
}

export async function fetchSessions(): Promise<Session[]> {
  const response = await fetch("/api/v1/users/me/sessions", {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("sessions");
  }
  const body = (await response.json()) as { items: Session[] };
  return body.items;
}

export function isStaff(me: Me | null | undefined): boolean {
  if (!me) {
    return false;
  }
  return me.roles.includes("super_admin") || me.roles.includes("staff");
}

export async function readProblem(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail || "Something went wrong.";
  } catch {
    return "Something went wrong.";
  }
}

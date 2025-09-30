export type Health = {
  status: "ok" | "down";
  db: "ok" | "down";
  redis: "ok" | "down";
};

export type Me = {
  id: string;
  email: string;
  email_verified_at: string | null;
  roles: string[];
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
    body: JSON.stringify(payload),
    cache: "no-store",
  });
}

export async function apiPost(path: string, payload: unknown, csrf: string): Promise<Response> {
  return apiSend("POST", path, payload, csrf);
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

export async function readProblem(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail || "Something went wrong.";
  } catch {
    return "Something went wrong.";
  }
}

"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { apiPost, fetchCsrfToken, readProblem } from "@/lib/api";

export function VerifyEmail({ token }: { token: string | null }) {
  const t = useTranslations("auth");
  const [status, setStatus] = useState<"working" | "ok" | "error">("working");
  const [detail, setDetail] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void (async () => {
      if (!token) {
        if (active) {
          setStatus("error");
          setDetail(t("missingToken"));
        }
        return;
      }
      try {
        const csrf = await fetchCsrfToken();
        const response = await apiPost("/api/v1/auth/verify-email", { token }, csrf);
        if (!active) {
          return;
        }
        if (!response.ok) {
          setStatus("error");
          setDetail(await readProblem(response));
          return;
        }
        setStatus("ok");
        setDetail(t("verifyOk"));
      } catch {
        if (active) {
          setStatus("error");
          setDetail(t("networkError"));
        }
      }
    })();
    return () => {
      active = false;
    };
  }, [token, t]);

  const className =
    status === "ok" ? "text-ok" : status === "error" ? "text-danger" : "text-muted";

  return (
    <p role="status" className={`text-sm ${className}`}>
      {status === "working" ? t("verifying") : detail}
    </p>
  );
}

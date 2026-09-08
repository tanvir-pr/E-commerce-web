export type LaunchCheck = {
  key: string;
  title: string;
  status: "pass" | "fail" | "warn" | "manual" | string;
  detail: string;
};

export type LaunchReadiness = {
  ready_for_launch: boolean;
  blocking_failures: number;
  manual_items: number;
  expected_alembic: string;
  checks: LaunchCheck[];
};

export async function fetchLaunchReadiness(): Promise<LaunchReadiness> {
  const response = await fetch("/api/v1/admin/launch-readiness", {
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Could not load launch readiness");
  }
  return (await response.json()) as LaunchReadiness;
}

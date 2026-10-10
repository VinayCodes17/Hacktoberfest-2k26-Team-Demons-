import type { components } from "./api.generated";

export type Readiness = components["schemas"]["Readiness"];

export async function getReadiness(): Promise<Readiness | null> {
  const base = process.env.HISABHPARAKH_API_URL ?? "http://127.0.0.1:8000";
  try {
    const response = await fetch(`${base}/api/v1/readiness`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok && response.status !== 503) return null;
    const body = await response.json();
    if (typeof body.service_ready !== "boolean" || typeof body.classification_ready !== "boolean" || !Array.isArray(body.checks)) return null;
    if (!body.checks.every((check: Record<string, unknown>) => check && typeof check.name === "string" && typeof check.message === "string" && ["ready", "blocked", "unavailable", "optional"].includes(String(check.status)))) return null;
    return body as Readiness;
  } catch {
    return null;
  }
}

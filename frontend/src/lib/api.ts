import type { Incident, IncidentCreate } from "@/types/incident";

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const message = await response.text();
    throw new Error(
      `API error ${response.status}: ${message || response.statusText}`
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

function normalizeIncidentList(data: unknown): Incident[] {
  // Supports a raw array or common paginated API response formats.
  if (Array.isArray(data)) {
    return data as Incident[];
  }

  if (data && typeof data === "object") {
    const result = data as Record<string, unknown>;

    for (const key of ["items", "incidents", "results", "data"]) {
      if (Array.isArray(result[key])) {
        return result[key] as Incident[];
      }
    }
  }

  throw new Error(
    "Unexpected incident-list response. Check the GET /incidents schema."
  );
}

export async function getIncidents(): Promise<Incident[]> {
  const data = await request<unknown>("/incidents");
  return normalizeIncidentList(data);
}

export async function getIncident(id: number | string): Promise<Incident> {
  return request<Incident>(`/incidents/${encodeURIComponent(String(id))}`);
}

export async function createIncident(
  payload: IncidentCreate
): Promise<Incident> {
  return request<Incident>("/incidents", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
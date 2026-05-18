const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api").replace(
  /\/$/,
  "",
);
const API_WITH_CREDENTIALS = import.meta.env.VITE_API_WITH_CREDENTIALS === "true";

export const USE_MOCKS = import.meta.env.VITE_USE_MOCKS === "true";
export const MAILGUARD_ACCOUNT_KEY = "mailguard.account";

export function getConnectedAccount() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(MAILGUARD_ACCOUNT_KEY) ?? "";
}

export function apiUrl(path: string) {
  const cleanPath = path.startsWith("/") ? path : `/${path}`;
  return `${API_BASE_URL}${cleanPath}`;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const account = getConnectedAccount();

  if (account) {
    headers.set("X-Mailguard-Account", account);
  }

  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(apiUrl(path), {
    ...init,
    headers,
    credentials: API_WITH_CREDENTIALS ? "include" : init.credentials,
  });

  if (!response.ok) {
    let message = `A solicitação falhou com status ${response.status}`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // Keep the status-based message when the response is not JSON.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

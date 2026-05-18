import { create } from "zustand";
import {
  MAILGUARD_ACCOUNT_KEY,
  USE_MOCKS,
  apiFetch,
  apiUrl,
} from "@/features/emails/api/apiClient";

const CONNECTED_KEY = "mailguard.connected";

interface AuthState {
  account: string;
  isConnected: boolean;
  loading: boolean;
  connect: () => Promise<void>;
  completeOAuthFromUrl: () => boolean;
  disconnect: () => void;
  deleteLocalData: () => Promise<void>;
  revokeGoogleAccess: () => Promise<boolean>;
}

function readAccount() {
  if (typeof window === "undefined") return "";
  return window.localStorage.getItem(MAILGUARD_ACCOUNT_KEY) ?? "";
}

function readConnected() {
  if (typeof window === "undefined") return false;
  return window.localStorage.getItem(CONNECTED_KEY) === "1" && Boolean(readAccount());
}

function persistConnection(account: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(CONNECTED_KEY, "1");
  window.localStorage.setItem(MAILGUARD_ACCOUNT_KEY, account);
}

export const useAuth = create<AuthState>((set) => ({
  account: readAccount(),
  isConnected: readConnected(),
  loading: false,
  connect: async () => {
    set({ loading: true });
    if (USE_MOCKS) {
      const account = "mock@example.com";
      persistConnection(account);
      set({ account, isConnected: true, loading: false });
      return;
    }

    if (typeof window !== "undefined") {
      window.location.assign(apiUrl("/auth/google/start/"));
    }
  },
  completeOAuthFromUrl: () => {
    if (typeof window === "undefined") return false;

    const url = new URL(window.location.href);
    const account = url.searchParams.get("account");
    const connected = url.searchParams.get("connected") === "1";
    if (!account || !connected) return false;

    persistConnection(account);
    set({ account, isConnected: true, loading: false });
    url.searchParams.delete("account");
    url.searchParams.delete("connected");
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    return true;
  },
  disconnect: () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(CONNECTED_KEY);
      window.localStorage.removeItem(MAILGUARD_ACCOUNT_KEY);
    }
    set({ account: "", isConnected: false, loading: false });
  },
  deleteLocalData: async () => {
    await apiFetch<{ deleted: boolean; account: string }>("/account/", { method: "DELETE" });
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(CONNECTED_KEY);
      window.localStorage.removeItem(MAILGUARD_ACCOUNT_KEY);
    }
    set({ account: "", isConnected: false, loading: false });
  },
  revokeGoogleAccess: async () => {
    const response = await apiFetch<{ revoked: boolean; account: string }>("/account/revoke/", {
      method: "POST",
    });
    return response.revoked;
  },
}));

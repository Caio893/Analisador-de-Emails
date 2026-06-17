import type { AnalyzeFolderResult, Email, Folder, InboxSummary, Paginated } from "../types";
import { MOCK_EMAILS, buildSummary } from "./emailsMock";
import { USE_MOCKS, apiFetch } from "./apiClient";

const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export interface FetchEmailsParams {
  folder: Folder;
  page?: number;
  pageSize?: number;
  search?: string;
}

function mockEmails({
  folder,
  page = 1,
  pageSize = 10,
  search = "",
}: FetchEmailsParams): Paginated<Email> {
  const q = search.trim().toLowerCase();
  const filtered = MOCK_EMAILS.filter(
    (e) =>
      e.folder === folder &&
      (q === "" ||
        e.subject.toLowerCase().includes(q) ||
        e.from.toLowerCase().includes(q) ||
        e.preview.toLowerCase().includes(q)),
  ).sort((a, b) => +new Date(b.time) - +new Date(a.time));

  const start = (page - 1) * pageSize;
  const items = filtered.slice(start, start + pageSize);
  return {
    items,
    page,
    pageSize,
    total: filtered.length,
    hasMore: start + pageSize < filtered.length,
  };
}

export async function fetchEmails(params: FetchEmailsParams): Promise<Paginated<Email>> {
  if (USE_MOCKS) {
    await delay(280);
    return mockEmails(params);
  }

  const search = new URLSearchParams({
    folder: params.folder,
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 10),
  });

  if (params.search?.trim()) {
    search.set("search", params.search.trim());
  }

  return apiFetch<Paginated<Email>>(`/emails/?${search.toString()}`);
}

export async function fetchEmail(id: string): Promise<Email | null> {
  if (USE_MOCKS) {
    await delay(120);
    return MOCK_EMAILS.find((e) => e.id === id) ?? null;
  }

  return apiFetch<Email>(`/emails/${id}/`);
}

export async function fetchSummary(): Promise<InboxSummary> {
  if (USE_MOCKS) {
    await delay(200);
    return buildSummary(MOCK_EMAILS);
  }

  return apiFetch<InboxSummary>("/summary/");
}

export async function fetchFolderCounts(): Promise<Record<Folder, number>> {
  if (USE_MOCKS) {
    await delay(100);
    return {
      inbox: MOCK_EMAILS.filter((e) => e.folder === "inbox").length,
      spam: MOCK_EMAILS.filter((e) => e.folder === "spam").length,
    };
  }

  const [inbox, spam] = await Promise.all([
    fetchEmails({ folder: "inbox", page: 1, pageSize: 1 }),
    fetchEmails({ folder: "spam", page: 1, pageSize: 1 }),
  ]);

  return {
    inbox: inbox.total,
    spam: spam.total,
  };
}

export async function syncEmails(folders: Folder[]): Promise<{
  synced: number;
  analyzed: number;
  localAnalyzed?: number;
  queued?: number;
  removed?: number;
}> {
  if (USE_MOCKS) {
    await delay(120);
    return { synced: MOCK_EMAILS.length, analyzed: 0, localAnalyzed: MOCK_EMAILS.length };
  }

  return apiFetch<{
    synced: number;
    analyzed: number;
    localAnalyzed?: number;
    queued?: number;
    removed?: number;
  }>("/emails/sync/", {
    method: "POST",
    body: JSON.stringify({ folders }),
  });
}

export async function analyzeFolder(folder: Folder): Promise<AnalyzeFolderResult> {
  if (USE_MOCKS) {
    await delay(1200);
    const total = MOCK_EMAILS.filter((e) => e.folder === folder).length;
    return {
      account: "mock@example.com",
      folder,
      total,
      eligible: total,
      skippedAlreadyAnalyzed: 0,
      analyzed: total,
      aiAnalyzed: total,
      localFallback: 0,
      trusted: 0,
      failed: 0,
      errors: [],
    };
  }

  return apiFetch<AnalyzeFolderResult>("/emails/analyze/", {
    method: "POST",
    body: JSON.stringify({ folder }),
  });
}

export async function trustEmailSender(
  emailId: string,
  ruleType: "email" | "domain",
): Promise<{ applied: boolean; detail: string | null; email: Email }> {
  if (USE_MOCKS) {
    await delay(120);
    const email = MOCK_EMAILS.find((item) => item.id === emailId);
    if (!email) throw new Error("Email nao encontrado.");
    return {
      applied: true,
      detail: null,
      email: {
        ...email,
        risk: "trusted",
        riskScore: 3,
        aiReason: "Classificado como confiavel por regra local.",
        trustedRule: {
          ruleType,
          value: ruleType === "email" ? email.fromEmail : email.fromEmail.split("@").pop() || "",
        },
      },
    };
  }

  return apiFetch<{ applied: boolean; detail: string | null; email: Email }>("/trusted-senders/", {
    method: "POST",
    body: JSON.stringify({ emailId, ruleType }),
  });
}

export async function removeEmailFromRadar(
  emailId: string,
): Promise<{ removed: boolean; id: string }> {
  if (USE_MOCKS) {
    await delay(120);
    return { removed: true, id: emailId };
  }

  return apiFetch<{ removed: boolean; id: string }>(`/emails/${emailId}/remove/`, {
    method: "POST",
  });
}

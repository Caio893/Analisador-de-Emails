import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  analyzeFolder,
  fetchEmail,
  fetchEmails,
  fetchFolderCounts,
  removeEmailFromRadar,
  syncEmails,
  trustEmailSender,
} from "../api/emailsApi";
import type { Email, Folder } from "../types";

const PAGE_SIZE = 8;
const EMAIL_SYNC_INTERVAL_MS = Math.max(
  60_000,
  Number(import.meta.env.VITE_EMAIL_SYNC_INTERVAL_MS ?? 300_000),
);

export function useEmails(folder: Folder, search: string) {
  return useInfiniteQuery({
    queryKey: ["emails", folder, search],
    initialPageParam: 1,
    queryFn: ({ pageParam }) =>
      fetchEmails({ folder, page: pageParam as number, pageSize: PAGE_SIZE, search }),
    getNextPageParam: (last) => (last.hasMore ? last.page + 1 : undefined),
    refetchInterval: (query) =>
      query.state.data?.pages.some((page) =>
        page.items.some((email) => email.analysisStatus === "pending"),
      )
        ? 5_000
        : false,
  });
}

export function useEmail(id: string | null) {
  return useQuery({
    queryKey: ["email", id],
    queryFn: () => (id ? fetchEmail(id) : Promise.resolve(null)),
    enabled: !!id,
    refetchInterval: (query) => (query.state.data?.analysisStatus === "pending" ? 5_000 : false),
  });
}

export function useFolderCounts() {
  return useQuery({
    queryKey: ["folder-counts"],
    queryFn: fetchFolderCounts,
  });
}

export function useSyncEmails(folder: Folder) {
  return useQuery({
    queryKey: ["email-sync", folder],
    queryFn: () => syncEmails([folder]),
    staleTime: EMAIL_SYNC_INTERVAL_MS,
    retry: false,
    refetchInterval: EMAIL_SYNC_INTERVAL_MS,
    refetchOnWindowFocus: false,
  });
}

export function useAnalyzeFolder() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (folder: Folder) => analyzeFolder(folder),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["emails"] });
      queryClient.invalidateQueries({ queryKey: ["email"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      queryClient.invalidateQueries({ queryKey: ["folder-counts"] });
    },
  });
}

export function useTrustEmailSender() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ emailId, ruleType }: { emailId: string; ruleType: "email" | "domain" }) =>
      trustEmailSender(emailId, ruleType),
    onSuccess: (result) => {
      queryClient.setQueryData<Email | null>(["email", result.email.id], (current) => {
        if (!current) return result.email;

        return {
          ...current,
          ...result.email,
          displayBodyHtml: result.email.displayBodyHtml ?? current.displayBodyHtml,
          displayBodyText: result.email.displayBodyText ?? current.displayBodyText,
          displayBodySource: result.email.displayBodySource ?? current.displayBodySource,
        };
      });
      queryClient.invalidateQueries({ queryKey: ["emails"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      queryClient.invalidateQueries({ queryKey: ["folder-counts"] });
    },
  });
}

export function useRemoveEmailFromRadar() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (emailId: string) => removeEmailFromRadar(emailId),
    onSuccess: (result) => {
      queryClient.removeQueries({ queryKey: ["email", result.id] });
      queryClient.invalidateQueries({ queryKey: ["emails"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
      queryClient.invalidateQueries({ queryKey: ["folder-counts"] });
    },
  });
}

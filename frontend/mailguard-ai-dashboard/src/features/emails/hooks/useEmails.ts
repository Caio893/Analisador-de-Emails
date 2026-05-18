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
import type { Folder } from "../types";

const PAGE_SIZE = 8;

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
    staleTime: 60_000,
    retry: false,
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
      queryClient.setQueryData(["email", result.email.id], result.email);
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

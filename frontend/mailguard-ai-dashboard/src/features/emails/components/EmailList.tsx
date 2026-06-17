import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, Loader2, Inbox, RefreshCw } from "lucide-react";
import { useEmails, useSyncEmails } from "../hooks/useEmails";
import { useEmailSelection } from "../store/emailSelectionStore";
import type { Folder } from "../types";
import { EmailListItem } from "./EmailListItem";
import { Button } from "@/components/ui/button";

interface Props {
  folder: Folder;
  search: string;
}

export function EmailList({ folder, search }: Props) {
  const q = useEmails(folder, search);
  const sync = useSyncEmails(folder);
  const queryClient = useQueryClient();
  const { selectedId, select } = useEmailSelection();
  const sentinel = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!sentinel.current) return;
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && q.hasNextPage && !q.isFetchingNextPage) {
          q.fetchNextPage();
        }
      },
      { rootMargin: "200px" },
    );
    obs.observe(sentinel.current);
    return () => obs.disconnect();
  }, [q]);

  useEffect(() => {
    if (sync.dataUpdatedAt > 0) {
      queryClient.invalidateQueries({ queryKey: ["emails", folder] });
      queryClient.invalidateQueries({ queryKey: ["folder-counts"] });
      queryClient.invalidateQueries({ queryKey: ["summary"] });
    }
  }, [folder, queryClient, sync.dataUpdatedAt]);

  if (q.isLoading) {
    return (
      <div className="space-y-2 p-3">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-20 animate-pulse rounded-xl bg-secondary/40" />
        ))}
      </div>
    );
  }

  const items = q.data?.pages.flatMap((p) => p.items) ?? [];
  const syncError = sync.error instanceof Error ? sync.error.message : "";
  const syncChanged = (sync.data?.synced ?? 0) + (sync.data?.removed ?? 0);
  const syncStatus = sync.isFetching
    ? "Sincronizando..."
    : sync.isError
      ? "Falha ao sincronizar"
      : sync.dataUpdatedAt > 0 && syncChanged > 0
        ? `${sync.data?.synced ?? 0} atualizados, ${sync.data?.removed ?? 0} removidos`
        : "";

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-12 text-center text-muted-foreground">
        {sync.isFetching ? (
          <Loader2 className="h-8 w-8 animate-spin opacity-40" />
        ) : (
          <Inbox className="h-8 w-8 opacity-40" />
        )}
        <p className="text-sm">
          {sync.isFetching ? "Sincronizando e-mails..." : "Nenhum e-mail por aqui."}
        </p>
        {q.isError && (
          <p className="max-w-sm text-xs text-risk-suspicious">{(q.error as Error).message}</p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 p-2">
      <div className="mb-1 flex items-center justify-between gap-2 rounded-lg border border-border/70 bg-card/70 px-2 py-1.5 text-xs text-muted-foreground">
        <div className="flex min-w-0 items-center gap-1.5">
          {sync.isFetching ? (
            <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
          ) : sync.isError ? (
            <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-risk-suspicious" />
          ) : null}
          <span className="truncate">
            {syncError || syncStatus || "E-mails sincronizados automaticamente."}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => sync.refetch()}
          disabled={sync.isFetching}
          className="h-7 shrink-0 px-2 text-xs"
        >
          <RefreshCw className="mr-1 h-3 w-3" />
          Atualizar
        </Button>
      </div>
      {items.map((e) => (
        <EmailListItem key={e.id} email={e} selected={selectedId === e.id} onSelect={select} />
      ))}
      <div ref={sentinel} className="h-6" />
      {q.hasNextPage && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => q.fetchNextPage()}
          disabled={q.isFetchingNextPage}
          className="mx-auto mt-2 text-xs text-muted-foreground"
        >
          {q.isFetchingNextPage ? <Loader2 className="mr-1 h-3 w-3 animate-spin" /> : null}
          Carregar mais
        </Button>
      )}
    </div>
  );
}

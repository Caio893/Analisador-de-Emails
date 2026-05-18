import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Loader2, Inbox } from "lucide-react";
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

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-2 p-12 text-center text-muted-foreground">
        {sync.isFetching ? <Loader2 className="h-8 w-8 animate-spin opacity-40" /> : <Inbox className="h-8 w-8 opacity-40" />}
        <p className="text-sm">
          {sync.isFetching ? "Sincronizando e-mails..." : "Nenhum e-mail por aqui."}
        </p>
        {q.isError && (
          <p className="max-w-sm text-xs text-risk-suspicious">
            {(q.error as Error).message}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-1 p-2">
      {items.map((e) => (
        <EmailListItem
          key={e.id}
          email={e}
          selected={selectedId === e.id}
          onSelect={select}
        />
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

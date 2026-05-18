import { useEffect, useState } from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  ChevronLeft,
  ChevronRight,
  Inbox,
  Loader2,
  ShieldAlert,
  Sparkles,
  UserRound,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { useAnalyzeFolder, useFolderCounts } from "@/features/emails/hooks/useEmails";
import type { Folder } from "@/features/emails/types";

type NavItem = {
  to: "/app/inbox" | "/app/spam";
  label: string;
  icon: typeof Inbox;
  badge?: number;
};

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const { data: counts } = useFolderCounts();
  const analyzeFolder = useAnalyzeFolder();
  const activeFolder: Folder | null =
    pathname === "/app/spam" ? "spam" : pathname === "/app/inbox" ? "inbox" : null;
  const activeFolderLabel = activeFolder === "spam" ? "Spam" : "Caixa de Entrada";
  const analyzeError = analyzeFolder.error instanceof Error ? analyzeFolder.error.message : "";
  const analyzeSummary = analyzeFolder.data
    ? analyzeFolder.data.total === 0
      ? "Nenhum email nesta pasta."
      : analyzeFolder.data.eligible === 0
        ? `${analyzeFolder.data.skippedAlreadyAnalyzed} emails ja estavam analisados.`
        : analyzeFolder.data.localFallback > 0
          ? `${analyzeFolder.data.aiAnalyzed} novos avaliados pela IA; ${analyzeFolder.data.localFallback} ficaram em triagem local.`
          : analyzeFolder.data.failed > 0
            ? `${analyzeFolder.data.aiAnalyzed} novos avaliados pela IA; ${analyzeFolder.data.failed} falharam.`
            : `${analyzeFolder.data.aiAnalyzed} novos avaliados pela IA.`
    : "";

  const items: NavItem[] = [
    { to: "/app/inbox", label: "Caixa de Entrada", icon: Inbox, badge: counts?.inbox },
    { to: "/app/spam", label: "Spam", icon: ShieldAlert, badge: counts?.spam },
  ];

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 767px)");
    const syncCollapsed = () => setCollapsed(mediaQuery.matches);

    syncCollapsed();
    mediaQuery.addEventListener("change", syncCollapsed);
    return () => mediaQuery.removeEventListener("change", syncCollapsed);
  }, []);

  return (
    <aside
      className={cn(
        "flex h-dvh shrink-0 flex-col overflow-hidden border-r border-sidebar-border bg-sidebar transition-[width] duration-200",
        collapsed ? "w-16" : "w-60",
      )}
    >
      <div
        className={cn(
          "flex h-14 items-center border-b border-sidebar-border",
          collapsed ? "justify-center px-2" : "gap-2 px-3",
        )}
      >
        {collapsed ? null : (
          <>
            <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary-glow shadow-[var(--shadow-glow)]">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <div className="min-w-0 flex-1 leading-tight">
              <div className="truncate text-sm font-semibold text-foreground">Email Radar</div>
              <div className="text-[10px] uppercase tracking-widest text-primary">IA</div>
            </div>
          </>
        )}
        <Button
          type="button"
          variant="ghost"
          size="icon"
          aria-label={collapsed ? "Expandir menu" : "Recolher menu"}
          title={collapsed ? "Expandir menu" : "Recolher menu"}
          onClick={() => setCollapsed((value) => !value)}
          className="h-8 w-8 shrink-0 text-sidebar-foreground/70 hover:text-sidebar-foreground"
        >
          {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
        </Button>
      </div>

      <div className={cn("flex flex-1 flex-col", collapsed ? "p-2" : "p-2")}>
        <nav className="space-y-1">
          {items.map(({ to, label, icon: Icon, badge }) => {
            const active = pathname === to;
            return (
              <Link
                key={to}
                to={to}
                title={collapsed ? label : undefined}
                className={cn(
                  "group relative flex h-10 items-center rounded-lg text-sm transition-colors",
                  collapsed ? "justify-center px-0" : "gap-3 px-3",
                  active
                    ? "bg-sidebar-accent text-sidebar-accent-foreground"
                    : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
                )}
              >
                {active && (
                  <span className="absolute inset-y-1 left-0 w-[3px] rounded-r-full bg-primary shadow-[0_0_8px_var(--primary)]" />
                )}
                <Icon className="h-4 w-4" />
                <span className={cn("min-w-0 flex-1 truncate", collapsed && "sr-only")}>
                  {label}
                </span>
                {typeof badge === "number" && badge > 0 && (
                  <span
                    className={cn(
                      "rounded-full bg-secondary text-[10px] font-medium text-foreground/80",
                      collapsed ? "absolute right-1 top-1 px-1" : "px-2 py-0.5",
                    )}
                  >
                    {badge}
                  </span>
                )}
              </Link>
            );
          })}
        </nav>

        {activeFolder ? (
          <div
            className={cn(
              "mt-6 rounded-xl border border-ai-action/35 bg-ai-action/10 shadow-[var(--shadow-attention)]",
              collapsed ? "p-1.5" : "p-3",
            )}
          >
            <Button
              type="button"
              disabled={analyzeFolder.isPending}
              onClick={() => analyzeFolder.mutate(activeFolder)}
              title="Analisar com IA"
              className={cn(
                "w-full rounded-xl bg-ai-action font-semibold text-ai-action-foreground shadow-[var(--shadow-attention)] transition-all hover:-translate-y-0.5 hover:bg-ai-action/90 focus-visible:ring-ai-action/40 disabled:hover:translate-y-0 animate-ai-attention",
                collapsed ? "h-11 px-0" : "h-12 px-3 text-sm",
              )}
            >
              {analyzeFolder.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              <span className={cn(collapsed && "sr-only")}>
                {analyzeFolder.isPending ? "Analisando..." : "Analisar com IA"}
              </span>
            </Button>
            {!collapsed ? (
              <>
                <p className="mt-2 text-[10px] leading-snug text-sidebar-foreground/70">
                  {analyzeFolder.isPending
                    ? `IA analisando ${activeFolderLabel}.`
                    : analyzeError ||
                      analyzeSummary ||
                      "A IA revisa a pasta selecionada quando voce clicar."}
                </p>
                {analyzeFolder.isPending ? (
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-card/70">
                    <div className="h-full w-2/3 animate-pulse rounded-full bg-ai-action" />
                  </div>
                ) : null}
              </>
            ) : null}
          </div>
        ) : null}

        <div className="flex-1" />
      </div>

      {!collapsed ? (
        <div className="border-t border-sidebar-border p-3">
          <Link
            to="/app/profile"
            className={cn(
              "mb-3 flex h-10 items-center gap-3 rounded-lg px-3 text-sm transition-colors",
              pathname === "/app/profile"
                ? "bg-sidebar-accent text-sidebar-accent-foreground"
                : "text-sidebar-foreground/80 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground",
            )}
          >
            <UserRound className="h-4 w-4" />
            <span className="min-w-0 flex-1 truncate">Perfil</span>
          </Link>
          <div className="rounded-lg bg-card/40 p-3">
            <div className="flex items-center gap-2 text-[11px] font-medium text-foreground/80">
              <span className="relative flex h-2 w-2">
                <span className="relative inline-flex h-2 w-2 rounded-full bg-risk-safe" />
              </span>
              IA sob demanda
            </div>
            <p className="mt-1 text-[10px] leading-snug text-muted-foreground">
              Sincronizacao usa triagem local. A IA roda somente pelo botao Analisar.
            </p>
          </div>
          <nav
            aria-label="Links legais"
            className="mt-3 flex items-center justify-center gap-3 text-[10px] text-muted-foreground"
          >
            <a href="/privacy" className="transition-colors hover:text-primary">
              Privacidade
            </a>
            <span aria-hidden className="h-1 w-1 rounded-full bg-muted-foreground/40" />
            <a href="/terms" className="transition-colors hover:text-primary">
              Termos
            </a>
          </nav>
        </div>
      ) : null}
    </aside>
  );
}

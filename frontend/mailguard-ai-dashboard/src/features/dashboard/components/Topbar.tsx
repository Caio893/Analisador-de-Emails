import { LogOut, Search, Sparkles } from "lucide-react";
import { useNavigate } from "@tanstack/react-router";
import { useAuth } from "@/features/auth/store/authStore";
import { Button } from "@/components/ui/button";

interface Props {
  search: string;
  onSearch: (v: string) => void;
}

export function Topbar({ search, onSearch }: Props) {
  const disconnect = useAuth((s) => s.disconnect);
  const navigate = useNavigate();

  return (
    <header className="flex h-14 items-center gap-2 border-b border-border/70 bg-card/85 px-2 shadow-sm backdrop-blur sm:gap-3 sm:px-4">
      <div className="relative min-w-0 flex-1 sm:max-w-xl">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          value={search}
          onChange={(e) => onSearch(e.target.value)}
          placeholder="Pesquisar e-mails, remetentes ou assuntos..."
          className="h-9 w-full rounded-lg border border-border bg-card/60 pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/30"
        />
      </div>

      <div className="ml-auto flex shrink-0 items-center gap-1 sm:gap-3">
        <div className="hidden items-center gap-2 rounded-full border border-primary/25 bg-primary/10 px-3 py-1 text-xs text-primary md:flex">
          <Sparkles className="h-3 w-3" />
          IA sob demanda
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            disconnect();
            navigate({ to: "/" });
          }}
          className="text-muted-foreground hover:text-foreground"
        >
          <LogOut className="h-3.5 w-3.5 sm:mr-1" />
          <span className="hidden sm:inline">Sair</span>
        </Button>
      </div>
    </header>
  );
}

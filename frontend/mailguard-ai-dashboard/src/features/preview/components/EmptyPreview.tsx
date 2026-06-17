import { Sparkles } from "lucide-react";

export function EmptyPreview() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 bg-secondary/25 px-8 text-center">
      <div className="rounded-lg bg-card p-4 shadow-sm ring-1 ring-border/70">
        <Sparkles className="h-7 w-7 text-primary" />
      </div>
      <div className="max-w-sm">
        <p className="text-base font-semibold text-foreground">Selecione um e-mail</p>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          O diagnostico da IA, o remetente e o dominio aparecem no topo da leitura.
        </p>
      </div>
    </div>
  );
}

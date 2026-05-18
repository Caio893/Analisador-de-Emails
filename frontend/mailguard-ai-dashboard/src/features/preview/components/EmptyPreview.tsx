import { Sparkles } from "lucide-react";

export function EmptyPreview() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-8 text-center">
      <div className="rounded-full bg-primary/10 p-4 ring-1 ring-primary/20">
        <Sparkles className="h-6 w-6 text-primary" />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">Selecione um e-mail</p>
        <p className="mt-1 text-xs text-muted-foreground">
          A IA analisa cada mensagem em tempo real e exibe aqui o motivo da classificação.
        </p>
      </div>
    </div>
  );
}

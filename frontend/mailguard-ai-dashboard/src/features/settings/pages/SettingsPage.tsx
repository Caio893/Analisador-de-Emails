import { DashboardLayout } from "@/features/dashboard/layout/DashboardLayout";

export function SettingsPage() {
  return (
    <DashboardLayout
      folder="inbox"
      title="Configurações"
      customMain={
        <div className="mx-auto max-w-2xl p-8">
          <h1 className="text-xl font-semibold text-foreground">Configurações</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Em breve: ajustes de IA, regras personalizadas e integração avançada com Gmail.
          </p>
          <div className="mt-6 space-y-3">
            {[
              ["Sensibilidade da IA", "Equilibrada"],
              ["Mover automaticamente para spam", "Ativo"],
              ["Notificações de phishing", "Ativo"],
            ].map(([k, v]) => (
              <div
                key={k}
                className="flex items-center justify-between rounded-lg border border-border/60 bg-card/50 px-4 py-3"
              >
                <span className="text-sm text-foreground">{k}</span>
                <span className="text-xs text-muted-foreground">{v}</span>
              </div>
            ))}
          </div>
        </div>
      }
    />
  );
}

import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { DashboardLayout } from "@/features/dashboard/layout/DashboardLayout";
import { useAuth } from "@/features/auth/store/authStore";
import { Button } from "@/components/ui/button";
import { ExternalLink, KeyRound, LogOut, Trash2 } from "lucide-react";

export function ProfilePage() {
  const { account, deleteLocalData, disconnect, revokeGoogleAccess } = useAuth();
  const navigate = useNavigate();
  const initials = (account || "ER").slice(0, 2).toUpperCase();
  const [statusMessage, setStatusMessage] = useState("");
  const [busyAction, setBusyAction] = useState<"delete" | "revoke" | "">("");

  const handleRevoke = async () => {
    setBusyAction("revoke");
    setStatusMessage("");
    try {
      const revoked = await revokeGoogleAccess();
      setStatusMessage(
        revoked
          ? "A solicitacao de revogacao foi enviada ao Google."
          : "Nao foi possivel confirmar a revogacao pelo aplicativo. Use tambem o link de permissoes da Conta Google.",
      );
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Falha ao revogar acesso OAuth.");
    } finally {
      setBusyAction("");
    }
  };

  const handleDeleteLocalData = async () => {
    const confirmed = window.confirm(
      "Excluir os dados locais remove a conta conectada, e-mails sincronizados, analises e regras salvas neste aplicativo. O acesso no Google deve ser revogado separadamente se ainda estiver ativo.",
    );
    if (!confirmed) return;

    setBusyAction("delete");
    setStatusMessage("");
    try {
      await deleteLocalData();
      navigate({ to: "/" });
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Falha ao excluir dados locais.");
    } finally {
      setBusyAction("");
    }
  };

  return (
    <DashboardLayout
      folder="inbox"
      title="Perfil"
      customMain={
        <div className="mx-auto max-w-2xl p-8">
          <h1 className="text-xl font-semibold text-foreground">Perfil</h1>
          <div className="mt-6 rounded-lg border border-border/60 bg-card/60 p-5">
            <div className="flex items-center gap-4">
              <div className="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary-glow text-base font-semibold text-primary-foreground">
                {initials}
              </div>
              <div className="flex-1">
                <div className="text-sm font-semibold text-foreground">Conta Google conectada</div>
                <div className="text-xs text-muted-foreground">
                  {account || "Nenhuma conta local"}
                </div>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  disconnect();
                  navigate({ to: "/" });
                }}
              >
                <LogOut className="mr-1 h-3.5 w-3.5" />
                Desconectar sessao
              </Button>
            </div>

            <div className="mt-5 grid gap-3 border-t border-border/60 pt-5 text-sm text-muted-foreground">
              <p>
                Voce pode encerrar esta sessao local, solicitar revogacao do token OAuth usado pelo
                aplicativo, abrir as permissoes da Conta Google ou excluir os dados locais
                associados a esta conexao.
              </p>
              {statusMessage ? (
                <p className="rounded-md border border-border/60 bg-background/60 p-3 text-xs">
                  {statusMessage}
                </p>
              ) : null}
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRevoke}
                  disabled={!account || Boolean(busyAction)}
                >
                  <KeyRound className="mr-1 h-3.5 w-3.5" />
                  {busyAction === "revoke" ? "Revogando..." : "Revogar token OAuth"}
                </Button>
                <Button asChild variant="outline" size="sm">
                  <a
                    href="https://myaccount.google.com/permissions"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <ExternalLink className="mr-1 h-3.5 w-3.5" />
                    Revogar no Google
                  </a>
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDeleteLocalData}
                  disabled={!account || Boolean(busyAction)}
                >
                  <Trash2 className="mr-1 h-3.5 w-3.5" />
                  {busyAction === "delete" ? "Excluindo..." : "Excluir dados locais"}
                </Button>
              </div>
              <p className="text-xs">
                Para pedidos formais de privacidade ou exclusao em backups, envie mensagem para{" "}
                <a
                  href="mailto:suporte@email-radar.com?subject=Excluir%20dados%20do%20Email%20Radar"
                  className="text-primary underline-offset-4 hover:underline"
                >
                  suporte@email-radar.com
                </a>
                .
              </p>
            </div>
          </div>
        </div>
      }
    />
  );
}

import { useState } from "react";
import { motion } from "framer-motion";
import { ShieldCheck, Sparkles, Zap } from "lucide-react";
import { ConnectGmailButton } from "@/features/auth/components/ConnectGmailButton";

export function LandingPage() {
  const [acceptedGoogleAccess, setAcceptedGoogleAccess] = useState(false);
  const googleDisclosureId = "google-access-disclosure";

  return (
    <div className="relative min-h-screen overflow-hidden bg-background">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 0%, color-mix(in oklab, var(--primary) 22%, transparent), transparent 70%)",
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(var(--border) 1px, transparent 1px), linear-gradient(90deg, var(--border) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
          maskImage: "radial-gradient(ellipse at top, black 30%, transparent 70%)",
          opacity: 0.18,
        }}
      />

      <header className="relative z-10 mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary-glow shadow-[var(--shadow-glow)]">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          <div className="leading-tight">
            <div className="text-sm font-semibold">Email Radar</div>
            <div className="text-[10px] uppercase tracking-widest text-primary">
              Seguranca Gmail
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3 py-1 text-xs text-primary">
          <span className="relative flex h-1.5 w-1.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary" />
          </span>
          IA sob demanda
        </div>
      </header>

      <main className="relative z-10 mx-auto flex max-w-3xl flex-col items-center px-6 pb-24 pt-20 text-center">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="mb-5 inline-flex items-center gap-2 rounded-full border border-border/60 bg-card/60 px-3 py-1 text-xs text-muted-foreground"
        >
          <Zap className="h-3 w-3 text-primary" />
          Analise de seguranca com Gmail somente leitura
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.05 }}
          className="text-5xl font-semibold tracking-tight text-foreground md:text-6xl"
        >
          Entenda mensagens arriscadas do Gmail{" "}
          <span className="bg-gradient-to-r from-primary to-primary-glow bg-clip-text text-transparent">
            antes de clicar
          </span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.1 }}
          className="mt-5 max-w-2xl text-base text-muted-foreground md:text-lg"
        >
          O Email Radar conecta ao Gmail com acesso somente leitura e ajuda a identificar phishing,
          spam, golpes, remetentes falsificados, links suspeitos e padroes de risco.
        </motion.p>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.15 }}
          className="mt-10 flex w-full max-w-2xl flex-col items-center"
        >
          <div
            id={googleDisclosureId}
            className="w-full rounded-lg border border-border/70 bg-card/50 p-4 text-left text-sm text-muted-foreground"
          >
            <p className="font-medium text-foreground">Antes de continuar com Google</p>
            <p className="mt-2">
              O Email Radar solicita acesso somente leitura ao Gmail para analisar mensagens em
              busca de phishing, spam, golpes, remetentes falsificados, links suspeitos, metadados
              de anexos e outros sinais de risco. Podemos processar remetente, assunto, cabecalhos,
              snippets, texto do corpo, links, marcadores e metadados de anexos para exibir uma
              pontuacao de risco e uma explicacao.
            </p>
            <p className="mt-2">
              O Email Radar nao pode enviar, editar, mover ou apagar seus e-mails. A analise por IA
              e usada apenas para entregar o resultado de seguranca visivel para voce, e dados do
              Gmail nao sao usados para criar, treinar ou melhorar modelos gerais de IA.
            </p>
            <p className="mt-2">
              O uso de informacoes recebidas das APIs do Google Workspace seguira a Politica de
              Dados do Usuario do Google, incluindo os requisitos de Uso Limitado.
            </p>
          </div>

          <label className="mt-4 flex w-full items-start gap-3 rounded-lg border border-border/60 bg-background/50 p-3 text-left text-xs text-muted-foreground">
            <input
              type="checkbox"
              checked={acceptedGoogleAccess}
              onChange={(event) => setAcceptedGoogleAccess(event.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-border accent-primary"
            />
            <span>
              Li e entendo como o Email Radar usa acesso somente leitura ao Gmail, e concordo com a{" "}
              <a href="/privacy" className="text-primary underline-offset-4 hover:underline">
                Politica de Privacidade
              </a>{" "}
              e os{" "}
              <a href="/terms" className="text-primary underline-offset-4 hover:underline">
                Termos de Servico
              </a>
              .
            </span>
          </label>

          <div className="mt-4">
            <ConnectGmailButton disabled={!acceptedGoogleAccess} describedBy={googleDisclosureId} />
          </div>
          <p className="mt-3 text-xs text-muted-foreground">
            Voce sera redirecionado ao Google para revisar e autorizar o escopo Gmail somente
            leitura.
          </p>
        </motion.div>

        <motion.nav
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.2 }}
          aria-label="Links legais"
          className="mt-5 flex items-center gap-4 text-xs text-muted-foreground"
        >
          <a href="/privacy" className="transition-colors hover:text-primary">
            Politica de Privacidade
          </a>
          <span aria-hidden className="h-1 w-1 rounded-full bg-muted-foreground/40" />
          <a href="/terms" className="transition-colors hover:text-primary">
            Termos de Servico
          </a>
        </motion.nav>

        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.25 }}
          className="mt-16 grid w-full grid-cols-1 gap-3 md:grid-cols-3"
        >
          {[
            {
              Icon: ShieldCheck,
              title: "Deteccao de phishing e golpes",
              text: "Analisa remetentes, links, cabecalhos e texto da mensagem em busca de sinais de ataque.",
            },
            {
              Icon: Sparkles,
              title: "Pontuacao de risco explicavel",
              text: "Mostra uma nota de 0 a 100 com uma justificativa curta e facil de entender.",
            },
            {
              Icon: Zap,
              title: "Gmail permanece somente leitura",
              text: "O Email Radar pode analisar mensagens, mas nao pode enviar, editar ou apagar emails.",
            },
          ].map(({ Icon, title, text }) => (
            <div
              key={title}
              className="rounded-xl border border-border/60 bg-card/40 p-4 text-left backdrop-blur"
            >
              <Icon className="h-4 w-4 text-primary" />
              <div className="mt-2 text-sm font-medium text-foreground">{title}</div>
              <p className="mt-1 text-xs text-muted-foreground">{text}</p>
            </div>
          ))}
        </motion.div>
      </main>
    </div>
  );
}

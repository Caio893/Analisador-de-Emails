import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ArrowLeft, Loader2, ShieldCheck, Sparkles, Trash2 } from "lucide-react";
import {
  useEmail,
  useRemoveEmailFromRadar,
  useTrustEmailSender,
} from "@/features/emails/hooks/useEmails";
import { useEmailSelection } from "@/features/emails/store/emailSelectionStore";
import { RiskBadge } from "@/features/emails/components/RiskBadge";
import type { Email } from "@/features/emails/types";
import { formatDateTime, initials } from "@/shared/lib/format";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { EmptyPreview } from "./EmptyPreview";

function friendlyAiReason(reason: string, status?: string) {
  if (status === "pending") {
    return "Analise local ainda nao disponivel.";
  }

  if (status === "local") {
    if (!/IA ainda nao foi executada|Basic local scan only/i.test(reason)) {
      return reason;
    }
    return "Analise local preliminar. A IA ainda nao avaliou esta mensagem. Use o botao Analisar na barra lateral para revisar a pasta selecionada com IA.";
  }

  if (/ratelimit|openai analysis failed|local heuristic fallback/i.test(reason)) {
    return "A analise avancada esta temporariamente limitada. Aplicamos uma classificacao preliminar com regras locais.";
  }

  return reason;
}

const EMAIL_FRAME_HEAD = `
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="referrer" content="no-referrer" />
  <base target="_blank" />
  <style>
    html { background: #ffffff; }
    body {
      box-sizing: border-box;
      margin: 0;
      padding: 24px;
      color: #1f2937;
      background: #ffffff;
      font: 14px/1.6 Arial, Helvetica, sans-serif;
      overflow-wrap: anywhere;
    }
    img { max-width: 100%; height: auto; }
    table { max-width: 100%; border-collapse: collapse; }
    pre { white-space: pre-wrap; }
    a { color: #2563eb; }
    @media (max-width: 640px) {
      body { padding: 14px; }
      table, tbody, tr, td, div { max-width: 100% !important; }
      img { max-width: 100% !important; }
    }
  </style>
`;

function escapeHtml(value: string) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function linkifyText(value: string) {
  const escaped = escapeHtml(value);
  return escaped.replace(
    /https?:\/\/[^\s<]+/gi,
    (url) => `<a href="${url}" rel="noopener noreferrer">${url}</a>`,
  );
}

function buildEmailDocument(html: string, text: string) {
  const content = html.trim();
  if (!content) {
    return `<!doctype html><html><head>${EMAIL_FRAME_HEAD}</head><body><pre>${linkifyText(
      text,
    )}</pre></body></html>`;
  }

  if (/<head[\s>]/i.test(content)) {
    return content.replace(/<head([^>]*)>/i, `<head$1>${EMAIL_FRAME_HEAD}`);
  }

  if (/<html[\s>]/i.test(content)) {
    return content.replace(/<html([^>]*)>/i, `<html$1><head>${EMAIL_FRAME_HEAD}</head>`);
  }

  if (/<body[\s>]/i.test(content)) {
    return `<!doctype html><html><head>${EMAIL_FRAME_HEAD}</head>${content}</html>`;
  }

  return `<!doctype html><html><head>${EMAIL_FRAME_HEAD}</head><body>${content}</body></html>`;
}

function RenderedEmailBody({
  html,
  text,
  subject,
}: {
  html?: string;
  text: string;
  subject: string;
}) {
  const hasContent = Boolean(html?.trim() || text.trim());
  if (!hasContent) {
    return (
      <div className="rounded-md border border-border bg-card p-6 text-sm text-muted-foreground">
        Esta mensagem nao tem corpo para exibir.
      </div>
    );
  }

  return (
    <iframe
      title={`Conteudo do email: ${subject || "sem assunto"}`}
      sandbox="allow-popups allow-popups-to-escape-sandbox"
      referrerPolicy="no-referrer"
      srcDoc={buildEmailDocument(html ?? "", text)}
      className="h-[calc(100vh-230px)] min-h-[560px] w-full rounded-md border border-border bg-white sm:h-[72vh]"
    />
  );
}

function SenderTrustPanel({
  email,
  senderDomain,
  trustDisabled,
  isTrusting,
  trustDetail,
  isRemoving,
  onTrustSender,
  onTrustDomain,
  onRemove,
}: {
  email: Email;
  senderDomain: string;
  trustDisabled: boolean;
  isTrusting: boolean;
  trustDetail?: string | null;
  isRemoving: boolean;
  onTrustSender: () => void;
  onTrustDomain: () => void;
  onRemove: () => void;
}) {
  return (
    <div className="rounded-lg border border-border/70 bg-card p-4 shadow-sm sm:p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold">
          {initials(email.from)}
        </div>
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-foreground">{email.from}</p>
          <p className="mt-0.5 break-all text-xs leading-5 text-muted-foreground">
            {email.fromEmail}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{formatDateTime(email.time)}</p>
          <div className="mt-3">
            <RiskBadge risk={email.risk} />
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
        <Button
          variant="outline"
          size="sm"
          disabled={trustDisabled}
          onClick={onTrustSender}
          className="h-9 justify-start text-xs"
        >
          {isTrusting ? (
            <Loader2 className="mr-1 h-3 w-3 animate-spin" />
          ) : (
            <ShieldCheck className="mr-1 h-3 w-3" />
          )}
          Confiar remetente
        </Button>
        {senderDomain ? (
          <Button
            variant="outline"
            size="sm"
            disabled={trustDisabled}
            onClick={onTrustDomain}
            className="h-9 justify-start text-xs"
          >
            <ShieldCheck className="mr-1 h-3 w-3" />
            Confiar dominio
          </Button>
        ) : null}
      </div>

      {email.trustedRule ? (
        <p className="mt-3 text-xs leading-5 text-risk-safe">
          Regra confiavel ativa: {email.trustedRule.ruleType === "email" ? "remetente" : "dominio"}{" "}
          {email.trustedRule.value}
        </p>
      ) : trustDetail ? (
        <p className="mt-3 text-xs leading-5 text-risk-suspicious">{trustDetail}</p>
      ) : null}

      <Button
        variant="ghost"
        size="sm"
        disabled={isRemoving}
        onClick={onRemove}
        className="mt-3 h-8 px-2 text-xs text-muted-foreground hover:text-risk-phishing"
      >
        {isRemoving ? (
          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
        ) : (
          <Trash2 className="mr-1 h-3 w-3" />
        )}
        Remover do Email Radar
      </Button>
    </div>
  );
}

function AiAnalysisPanel({ label, reason }: { label: string; reason: string }) {
  return (
    <div className="rounded-lg border border-border/70 bg-card p-4 shadow-sm sm:p-5">
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-primary">
        <Sparkles className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className="mt-3 text-sm leading-7 text-foreground/85">{reason}</p>
    </div>
  );
}

export function EmailPreviewPanel() {
  const [mobileInsightsOpen, setMobileInsightsOpen] = useState(false);
  const selectedId = useEmailSelection((s) => s.selectedId);
  const selectEmail = useEmailSelection((s) => s.select);
  const { data: email, isLoading } = useEmail(selectedId);
  const trustSender = useTrustEmailSender();
  const removeEmail = useRemoveEmailFromRadar();

  if (!selectedId) return <EmptyPreview />;
  if (isLoading || !email) {
    return (
      <div className="space-y-3 p-6">
        <div className="h-6 w-2/3 animate-pulse rounded bg-secondary/50" />
        <div className="h-4 w-1/3 animate-pulse rounded bg-secondary/50" />
        <div className="mt-6 h-40 animate-pulse rounded bg-secondary/40" />
      </div>
    );
  }

  const senderDomain = email.fromEmail.includes("@")
    ? email.fromEmail.split("@").pop() || ""
    : String(email.metadata?.sender_domain || "");
  const trustDisabled = trustSender.isPending || Boolean(email.trustedRule);
  const analysisLabel = email.analysisStatus === "local" ? "Analise local" : "Analise da IA";
  const analysisReason = friendlyAiReason(email.aiReason, email.analysisStatus);
  const renderTrustPanel = () => (
    <SenderTrustPanel
      email={email}
      senderDomain={senderDomain}
      trustDisabled={trustDisabled}
      isTrusting={trustSender.isPending}
      trustDetail={trustSender.data?.detail}
      isRemoving={removeEmail.isPending}
      onTrustSender={() => trustSender.mutate({ emailId: email.id, ruleType: "email" })}
      onTrustDomain={() => trustSender.mutate({ emailId: email.id, ruleType: "domain" })}
      onRemove={() => {
        removeEmail.mutate(email.id, {
          onSuccess: () => selectEmail(null),
        });
      }}
    />
  );

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={email.id}
        initial={{ opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -12 }}
        transition={{ duration: 0.18 }}
        className="flex h-full min-w-0 bg-background"
      >
        <div className="flex min-w-0 flex-1 flex-col">
          <div className="border-b border-border/60 bg-card/55 p-4 sm:p-6">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => selectEmail(null)}
                className="-ml-2 h-8 text-xs text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="mr-1 h-3.5 w-3.5" />
                Voltar para lista
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setMobileInsightsOpen(true)}
                className="h-8 text-xs lg:hidden"
              >
                <Sparkles className="mr-1 h-3.5 w-3.5" />
                Analise da IA
              </Button>
            </div>
            <h2 className="max-w-4xl text-lg font-semibold leading-snug text-foreground sm:text-xl">
              {email.subject}
            </h2>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-3 sm:px-6 sm:py-6">
            <div className="mx-auto max-w-5xl">
              <RenderedEmailBody
                html={email.displayBodyHtml}
                text={email.displayBodyText ?? email.body}
                subject={email.subject}
              />
            </div>
          </div>
        </div>

        <aside className="hidden w-[380px] shrink-0 border-l border-border/60 bg-card/40 p-5 lg:block">
          <div className="sticky top-5 space-y-5">
            {renderTrustPanel()}
            <AiAnalysisPanel label={analysisLabel} reason={analysisReason} />
          </div>
        </aside>

        <Sheet open={mobileInsightsOpen} onOpenChange={setMobileInsightsOpen}>
          <SheetContent
            side="bottom"
            className="max-h-[88vh] overflow-y-auto rounded-t-2xl border-border/70 p-4 sm:p-6 lg:hidden"
          >
            <SheetHeader className="pr-8 text-left">
              <SheetTitle>Analise e detalhes</SheetTitle>
              <SheetDescription>
                Informacoes do remetente, acoes de confianca e leitura da IA.
              </SheetDescription>
            </SheetHeader>
            <div className="mt-5 space-y-4">
              {renderTrustPanel()}
              <AiAnalysisPanel label={analysisLabel} reason={analysisReason} />
            </div>
          </SheetContent>
        </Sheet>
      </motion.div>
    </AnimatePresence>
  );
}

import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  CalendarClock,
  Globe2,
  Loader2,
  Paperclip,
  ShieldAlert,
  ShieldCheck,
  ShieldQuestion,
  ShieldX,
  Sparkles,
  Trash2,
} from "lucide-react";
import {
  useEmail,
  useRemoveEmailFromRadar,
  useTrustEmailSender,
} from "@/features/emails/hooks/useEmails";
import { useEmailSelection } from "@/features/emails/store/emailSelectionStore";
import { RiskBadge } from "@/features/emails/components/RiskBadge";
import type { Email, RiskLevel } from "@/features/emails/types";
import { formatDateTime, initials } from "@/shared/lib/format";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
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
      padding: 28px;
      color: #1f2937;
      background: #ffffff;
      font: 15px/1.7 Arial, Helvetica, sans-serif;
      overflow-wrap: anywhere;
    }
    img { max-width: 100%; height: auto; }
    table { max-width: 100%; border-collapse: collapse; }
    pre { white-space: pre-wrap; }
    a { color: #2563eb; }
    @media (max-width: 640px) {
      body { padding: 16px; }
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

const AI_DIAGNOSIS: Record<
  RiskLevel,
  {
    title: string;
    caption: string;
    Icon: typeof ShieldCheck;
    bannerClass: string;
    iconClass: string;
    scoreClass: string;
  }
> = {
  trusted: {
    title: "A IA classificou este e-mail como confiavel",
    caption: "Baixo risco",
    Icon: ShieldCheck,
    bannerClass: "border-risk-safe/35 bg-risk-safe/10",
    iconClass: "bg-risk-safe/15 text-risk-safe ring-risk-safe/25",
    scoreClass: "text-risk-safe",
  },
  slightly_trusted: {
    title: "A IA recomenda uma leitura com atencao",
    caption: "Risco moderado",
    Icon: ShieldQuestion,
    bannerClass: "border-primary/35 bg-primary/10",
    iconClass: "bg-primary/15 text-primary ring-primary/25",
    scoreClass: "text-primary",
  },
  suspicious: {
    title: "A IA encontrou sinais suspeitos",
    caption: "Risco elevado",
    Icon: ShieldAlert,
    bannerClass: "border-risk-suspicious/40 bg-risk-suspicious/12",
    iconClass: "bg-risk-suspicious/15 text-risk-suspicious ring-risk-suspicious/25",
    scoreClass: "text-risk-suspicious",
  },
  dangerous: {
    title: "A IA marcou este e-mail como perigoso",
    caption: "Alto risco",
    Icon: ShieldX,
    bannerClass: "border-risk-phishing/40 bg-risk-phishing/10",
    iconClass: "bg-risk-phishing/15 text-risk-phishing ring-risk-phishing/25",
    scoreClass: "text-risk-phishing",
  },
};

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
      <div className="flex h-full min-h-[360px] items-center justify-center rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
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
      className="h-[calc(100vh-340px)] min-h-[520px] w-full rounded-lg border border-border bg-white shadow-sm lg:h-full lg:min-h-[420px]"
    />
  );
}

function AiDiagnosisBanner({
  email,
  label,
  reason,
}: {
  email: Email;
  label: string;
  reason: string;
}) {
  const tone = AI_DIAGNOSIS[email.risk];
  const score = Math.max(0, Math.min(100, email.riskScore ?? 0));

  return (
    <section
      aria-label="Diagnostico da IA"
      className={cn("rounded-lg border p-3 shadow-sm sm:p-4", tone.bannerClass)}
    >
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 gap-3">
          <div
            className={cn(
              "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ring-1 sm:h-12 sm:w-12",
              tone.iconClass,
            )}
          >
            <tone.Icon className="h-5 w-5 sm:h-6 sm:w-6" />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1 rounded-full bg-card/75 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-foreground/70 ring-1 ring-border/70">
                <Sparkles className="h-3 w-3 text-primary" />
                {label}
              </span>
              <RiskBadge risk={email.risk} className="bg-card/75" />
            </div>
            <h2 className="mt-2 text-lg font-semibold leading-tight text-foreground sm:text-xl">
              {tone.title}
            </h2>
            <p className="mt-1.5 line-clamp-3 max-w-4xl text-sm leading-6 text-foreground/80">
              {reason}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center justify-between gap-4 rounded-lg border border-border/70 bg-card/80 px-3 py-2.5 lg:min-w-32 lg:flex-col lg:items-start">
          <div>
            <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
              Score de risco
            </p>
            <div className={cn("mt-1 text-2xl font-semibold leading-none", tone.scoreClass)}>
              {score}
              <span className="text-sm font-medium text-muted-foreground">/100</span>
            </div>
          </div>
          <p className="text-xs font-medium text-foreground/75">{tone.caption}</p>
        </div>
      </div>
    </section>
  );
}

function EmailHeader({
  email,
  senderDomain,
  trustDisabled,
  isTrustingSender,
  isTrustingDomain,
  trustDetail,
  isRemoving,
  onBack,
  onTrustSender,
  onTrustDomain,
  onRemove,
}: {
  email: Email;
  senderDomain: string;
  trustDisabled: boolean;
  isTrustingSender: boolean;
  isTrustingDomain: boolean;
  trustDetail?: string | null;
  isRemoving: boolean;
  onBack: () => void;
  onTrustSender: () => void;
  onTrustDomain: () => void;
  onRemove: () => void;
}) {
  return (
    <section className="rounded-lg border border-border/70 bg-card p-3 shadow-sm sm:p-4">
      <div className="mb-3 flex items-center justify-between gap-2 lg:hidden">
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="-ml-2 h-8 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-1 h-3.5 w-3.5" />
          Voltar
        </Button>
      </div>

      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="flex min-w-0 gap-3">
          <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-secondary text-sm font-semibold text-foreground ring-1 ring-border/70 sm:h-14 sm:w-14">
            {initials(email.from)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="min-w-0 break-words text-lg font-semibold leading-tight text-foreground sm:text-xl">
                {email.from}
              </h3>
              {senderDomain ? (
                <span className="inline-flex max-w-full items-center gap-1 rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
                  <Globe2 className="h-3.5 w-3.5 shrink-0" />
                  <span className="truncate">{senderDomain}</span>
                </span>
              ) : null}
            </div>
            <p className="mt-1 break-all text-sm text-muted-foreground">{email.fromEmail}</p>
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1 rounded-full bg-secondary/70 px-2.5 py-1">
                <CalendarClock className="h-3.5 w-3.5" />
                {formatDateTime(email.time)}
              </span>
              {email.hasAttachments ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-secondary/70 px-2.5 py-1">
                  <Paperclip className="h-3.5 w-3.5" />
                  {email.attachmentCount ?? 0} anexo(s)
                </span>
              ) : null}
            </div>
            <h1 className="mt-3 line-clamp-2 break-words text-base font-semibold leading-snug text-foreground sm:text-lg">
              {email.subject || "Sem assunto"}
            </h1>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 lg:max-w-[320px] lg:justify-end">
          <Button
            variant="outline"
            size="sm"
            disabled={trustDisabled}
            onClick={onTrustSender}
            className="h-9 text-xs"
          >
            {isTrustingSender ? (
              <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
            ) : (
              <ShieldCheck className="mr-1 h-3.5 w-3.5" />
            )}
            Confiar remetente
          </Button>
          {senderDomain ? (
            <Button
              variant="outline"
              size="sm"
              disabled={trustDisabled}
              onClick={onTrustDomain}
              className="h-9 text-xs"
            >
              {isTrustingDomain ? (
                <Loader2 className="mr-1 h-3.5 w-3.5 animate-spin" />
              ) : (
                <ShieldCheck className="mr-1 h-3.5 w-3.5" />
              )}
              Confiar dominio
            </Button>
          ) : null}
          <Button
            variant="ghost"
            size="icon"
            disabled={isRemoving}
            onClick={onRemove}
            aria-label="Remover do Email Radar"
            title="Remover do Email Radar"
            className="h-9 w-9 text-muted-foreground hover:text-risk-phishing"
          >
            {isRemoving ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <Trash2 className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
      </div>

      {email.trustedRule ? (
        <p className="mt-3 text-xs leading-5 text-risk-safe">
          Regra confiavel ativa: {email.trustedRule.ruleType === "email" ? "remetente" : "dominio"}{" "}
          {email.trustedRule.value}
        </p>
      ) : trustDetail ? (
        <p className="mt-3 text-xs leading-5 text-risk-suspicious">{trustDetail}</p>
      ) : null}
    </section>
  );
}

export function EmailPreviewPanel() {
  const selectedId = useEmailSelection((s) => s.selectedId);
  const selectEmail = useEmailSelection((s) => s.select);
  const { data: email, isLoading } = useEmail(selectedId);
  const trustSender = useTrustEmailSender();
  const removeEmail = useRemoveEmailFromRadar();

  if (!selectedId) return <EmptyPreview />;
  if (isLoading || !email) {
    return (
      <div className="space-y-4 p-5">
        <div className="h-28 animate-pulse rounded-lg bg-secondary/50" />
        <div className="h-32 animate-pulse rounded-lg bg-secondary/40" />
        <div className="h-72 animate-pulse rounded-lg bg-secondary/35" />
      </div>
    );
  }

  const senderDomain = email.fromEmail.includes("@")
    ? email.fromEmail.split("@").pop()?.toLowerCase() || ""
    : String(email.metadata?.sender_domain || "").toLowerCase();
  const trustDisabled = trustSender.isPending || Boolean(email.trustedRule);
  const trustingRuleType = trustSender.variables?.ruleType;
  const analysisLabel = email.analysisStatus === "local" ? "Analise local" : "Diagnostico da IA";
  const analysisReason = friendlyAiReason(email.aiReason, email.analysisStatus);

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={email.id}
        initial={{ opacity: 0, x: 12 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -12 }}
        transition={{ duration: 0.18 }}
        className="flex h-full min-w-0 flex-col bg-background"
      >
        <div className="shrink-0 border-b border-border/60 bg-background/95">
          <div className="mx-auto w-full max-w-7xl space-y-3 p-3 sm:p-4">
            <AiDiagnosisBanner email={email} label={analysisLabel} reason={analysisReason} />
            <EmailHeader
              email={email}
              senderDomain={senderDomain}
              trustDisabled={trustDisabled}
              isTrustingSender={trustSender.isPending && trustingRuleType === "email"}
              isTrustingDomain={trustSender.isPending && trustingRuleType === "domain"}
              trustDetail={trustSender.data?.detail}
              isRemoving={removeEmail.isPending}
              onBack={() => selectEmail(null)}
              onTrustSender={() => trustSender.mutate({ emailId: email.id, ruleType: "email" })}
              onTrustDomain={() => trustSender.mutate({ emailId: email.id, ruleType: "domain" })}
              onRemove={() => {
                removeEmail.mutate(email.id, {
                  onSuccess: () => selectEmail(null),
                });
              }}
            />
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto bg-secondary/25 px-3 py-3 sm:px-4 sm:py-4">
          <div className="mx-auto h-full max-w-6xl">
            <RenderedEmailBody
              html={email.displayBodyHtml}
              text={email.displayBodyText ?? email.body ?? ""}
              subject={email.subject}
            />
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}

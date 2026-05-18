import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { formatTime, initials } from "@/shared/lib/format";
import type { Email } from "../types";
import { RiskBadge } from "./RiskBadge";

interface Props {
  email: Email;
  selected: boolean;
  onSelect: (id: string) => void;
}

export function EmailListItem({ email, selected, onSelect }: Props) {
  return (
    <motion.button
      layout
      whileHover={{ x: 2 }}
      onClick={() => onSelect(email.id)}
      className={cn(
        "group relative flex w-full gap-3 rounded-xl border border-transparent px-3 py-3 text-left transition-colors",
        "hover:bg-accent/40",
        selected && "border-primary/40 bg-accent/60 shadow-[var(--shadow-elegant)]",
      )}
    >
      {selected && <span className="absolute inset-y-2 left-0 w-[3px] rounded-r-full bg-primary" />}
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-secondary text-xs font-semibold text-foreground/80">
        {initials(email.from)}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              "truncate text-sm",
              email.unread ? "font-semibold text-foreground" : "text-foreground/85",
            )}
          >
            {email.from}
          </span>
          <span className="ml-auto shrink-0 text-[11px] text-muted-foreground">
            {formatTime(email.time)}
          </span>
        </div>
        <div className="mt-0.5 truncate text-sm text-foreground/90">{email.subject}</div>
        <div className="mt-1 line-clamp-1 text-xs text-muted-foreground">{email.preview}</div>
        <div className="mt-2 flex items-center gap-2">
          <RiskBadge risk={email.risk} />
          {email.analysisStatus === "local" && (
            <span className="rounded-full border border-border bg-card px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
              Local
            </span>
          )}
          {email.analysisStatus === "pending" && (
            <span className="rounded-full border border-primary/30 bg-primary/10 px-2 py-0.5 text-[10px] font-medium text-primary">
              Pendente
            </span>
          )}
          {email.unread && (
            <span className="h-1.5 w-1.5 rounded-full bg-primary shadow-[0_0_8px_var(--primary)]" />
          )}
        </div>
      </div>
    </motion.button>
  );
}

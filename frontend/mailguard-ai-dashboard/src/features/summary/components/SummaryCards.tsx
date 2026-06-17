import { motion } from "framer-motion";
import { Mail, ShieldX, ShieldAlert } from "lucide-react";
import { useSummary } from "../hooks/useSummary";
import { cn } from "@/lib/utils";

export function SummaryCards({ compact = false }: { compact?: boolean }) {
  const { data, isLoading } = useSummary();

  const items = [
    { label: "Triados hoje", value: data?.analyzedToday ?? 0, Icon: Mail, tone: "text-primary" },
    {
      label: "Spam detectado",
      value: data?.spamDetected ?? 0,
      Icon: ShieldX,
      tone: "text-risk-phishing",
    },
    {
      label: "E-mails suspeitos",
      value: data?.suspicious ?? 0,
      Icon: ShieldAlert,
      tone: "text-risk-suspicious",
    },
  ];

  return (
    <div className={cn("grid gap-3", compact ? "grid-cols-3 gap-2" : "grid-cols-1 sm:grid-cols-3")}>
      {items.map((it, i) => (
        <motion.div
          key={it.label}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05, duration: 0.25 }}
          className={cn(
            "rounded-lg border border-border/60 bg-card/70 backdrop-blur",
            compact ? "p-2.5" : "p-4",
          )}
        >
          <div className="flex items-center justify-between">
            <span
              className={cn(
                "font-medium uppercase text-muted-foreground",
                compact ? "text-[9px] tracking-wide" : "text-[11px] tracking-wider",
              )}
            >
              {it.label}
            </span>
            <it.Icon className={cn(compact ? "h-3.5 w-3.5" : "h-4 w-4", it.tone)} />
          </div>
          <div
            className={cn("mt-2 font-semibold text-foreground", compact ? "text-lg" : "text-2xl")}
          >
            {isLoading ? <span className="text-muted-foreground/50">-</span> : it.value}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

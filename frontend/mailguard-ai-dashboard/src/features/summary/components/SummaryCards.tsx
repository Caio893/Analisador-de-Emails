import { motion } from "framer-motion";
import { Mail, ShieldX, ShieldAlert } from "lucide-react";
import { useSummary } from "../hooks/useSummary";

export function SummaryCards() {
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
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {items.map((it, i) => (
        <motion.div
          key={it.label}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.05, duration: 0.25 }}
          className="rounded-xl border border-border/60 bg-card/60 p-4 backdrop-blur"
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
              {it.label}
            </span>
            <it.Icon className={`h-4 w-4 ${it.tone}`} />
          </div>
          <div className="mt-2 text-2xl font-semibold text-foreground">
            {isLoading ? <span className="text-muted-foreground/50">-</span> : it.value}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

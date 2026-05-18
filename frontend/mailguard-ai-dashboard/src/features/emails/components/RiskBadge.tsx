import { ShieldCheck, ShieldAlert, ShieldX, ShieldQuestion } from "lucide-react";
import type { RiskLevel } from "../types";
import { cn } from "@/lib/utils";

const config: Record<
  RiskLevel,
  { label: string; cls: string; Icon: typeof ShieldCheck }
> = {
  trusted: {
    label: "Confiável",
    cls: "bg-risk-safe/15 text-risk-safe border-risk-safe/30",
    Icon: ShieldCheck,
  },
  slightly_trusted: {
    label: "Pouco confiável",
    cls: "bg-primary/15 text-primary border-primary/30",
    Icon: ShieldQuestion,
  },
  suspicious: {
    label: "Suspeito",
    cls: "bg-risk-suspicious/15 text-risk-suspicious border-risk-suspicious/30",
    Icon: ShieldAlert,
  },
  dangerous: {
    label: "Perigoso",
    cls: "bg-risk-phishing/15 text-risk-phishing border-risk-phishing/30",
    Icon: ShieldX,
  },
};

export function RiskBadge({ risk, className }: { risk: RiskLevel; className?: string }) {
  const { label, cls, Icon } = config[risk];
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium",
        cls,
        className,
      )}
    >
      <Icon className="h-3 w-3" />
      {label}
    </span>
  );
}

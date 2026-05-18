import type { RiskLevel } from "../types";

const colorFor = (risk: RiskLevel) =>
  risk === "trusted"
    ? "var(--risk-safe)"
    : risk === "slightly_trusted"
      ? "var(--primary)"
    : risk === "suspicious"
      ? "var(--risk-suspicious)"
      : "var(--risk-phishing)";

export function RiskScore({ score, risk }: { score: number; risk: RiskLevel }) {
  const color = colorFor(risk);
  return (
    <div className="flex items-center gap-3">
      <div className="relative h-16 w-16">
        <svg viewBox="0 0 36 36" className="h-16 w-16 -rotate-90">
          <circle cx="18" cy="18" r="15" fill="none" stroke="var(--border)" strokeWidth="3" />
          <circle
            cx="18"
            cy="18"
            r="15"
            fill="none"
            stroke={color}
            strokeWidth="3"
            strokeDasharray={`${(score / 100) * 94.25} 94.25`}
            strokeLinecap="round"
          />
        </svg>
        <div
          className="absolute inset-0 flex items-center justify-center text-sm font-semibold"
          style={{ color }}
        >
          {score}
        </div>
      </div>
      <div className="text-xs text-muted-foreground">
        <div className="text-foreground font-medium">Pontuação de risco</div>
        <div>0 = seguro | 100 = ameaça crítica</div>
      </div>
    </div>
  );
}

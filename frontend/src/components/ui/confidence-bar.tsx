import { cn } from "@/lib/utils";

interface ConfidenceBarProps {
  confidence: number;
  className?: string;
}

export default function ConfidenceBar({ confidence, className }: ConfidenceBarProps) {
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      <div className="flex-1 h-1.5 bg-card shadow-[var(--neu-pressed)] rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-primary to-accent rounded-full shadow-[var(--neu-glow)] transition-all duration-500"
          style={{ width: `${confidence}%` }}
        />
      </div>
      <span className="font-mono text-xs font-medium text-accent">{confidence}%</span>
    </div>
  );
}

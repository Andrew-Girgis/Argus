import { cn } from "@/lib/utils";

type ChipVariant = "default" | "success" | "warning" | "error";

interface InsightChipProps {
  label: string;
  confidence?: number;
  variant?: ChipVariant;
  className?: string;
}

const dotColors: Record<ChipVariant, string> = {
  default: "bg-primary shadow-[var(--neu-glow)]",
  success: "bg-success shadow-[0_0_8px_oklch(0.627_0.209_145.5_/_0.4)]",
  warning: "bg-warning shadow-[0_0_8px_oklch(0.702_0.164_79.5_/_0.4)]",
  error: "bg-destructive shadow-[0_0_8px_oklch(0.577_0.245_27.3_/_0.4)]",
};

const textColors: Record<ChipVariant, string> = {
  default: "text-accent",
  success: "text-success",
  warning: "text-warning",
  error: "text-destructive",
};

export default function InsightChip({
  label,
  confidence,
  variant = "default",
  className,
}: InsightChipProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 bg-card shadow-[var(--neu-pressed)] rounded-lg px-3 py-1.5",
        className,
      )}
    >
      <span
        className={cn(
          "size-1.5 rounded-full animate-[argus-pulse_2s_ease-in-out_infinite]",
          dotColors[variant],
        )}
      />
      <span
        className={cn(
          "font-mono text-xs font-medium tracking-wider",
          textColors[variant],
        )}
      >
        {label}
        {confidence != null && ` · ${confidence}%`}
      </span>
    </div>
  );
}

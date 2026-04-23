import { cn } from "@/lib/utils";

interface StatCalloutProps {
  label: string;
  value: string | number;
  className?: string;
}

export default function StatCallout({ label, value, className }: StatCalloutProps) {
  return (
    <div
      className={cn(
        "bg-card shadow-[var(--neu-flat)] rounded-2xl p-5 flex flex-col gap-1",
        className,
      )}
    >
      <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </span>
      <span className="font-mono text-2xl font-bold text-foreground tracking-tight">
        {value}
      </span>
    </div>
  );
}

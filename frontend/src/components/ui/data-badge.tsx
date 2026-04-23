import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface DataBadgeProps {
  children: React.ReactNode;
  className?: string;
  copyValue?: string;
}

export default function DataBadge({ children, className, copyValue }: DataBadgeProps) {
  const [copied, setCopied] = useState(false);

  const baseClass = cn(
    "inline-flex items-center gap-1.5 font-mono text-xs font-medium tracking-wider text-accent bg-card shadow-[var(--neu-pressed)] rounded-md px-2.5 py-1",
    className,
  );

  if (!copyValue) {
    return <span className={baseClass}>{children}</span>;
  }

  function handleCopy() {
    navigator.clipboard.writeText(copyValue!);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button
      onClick={handleCopy}
      title="Copy coordinates"
      className={cn(baseClass, "cursor-pointer transition-colors hover:text-foreground")}
    >
      {children}
      {copied
        ? <Check className="size-3 text-primary" />
        : <Copy className="size-3 opacity-50" />}
    </button>
  );
}

import { useState } from "react";
import { Code, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";

interface JsonViewerProps {
  data: unknown;
  title?: string;
}

export default function JsonViewer({ data, title = "Raw JSON" }: JsonViewerProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="w-full rounded-2xl bg-card shadow-[var(--neu-flat)] overflow-hidden">
      <Button
        variant="ghost"
        className="w-full justify-between rounded-none px-5 py-3.5 h-auto text-sm font-medium text-muted-foreground hover:text-foreground"
        onClick={() => setExpanded(!expanded)}
      >
        <span className="flex items-center gap-2">
          <Code className="size-4" />
          {title}
        </span>
        <ChevronDown
          className={`size-4 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
        />
      </Button>
      {expanded && (
        <div className="bg-surface-raised p-5 overflow-x-auto border-t border-border">
          <pre className="text-xs font-mono text-muted-foreground whitespace-pre-wrap break-words">
            <code>{JSON.stringify(data, null, 2)}</code>
          </pre>
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from "react";
import { Eye, EyeOff } from "lucide-react";

export default function ThemeToggle() {
  const [dark, setDark] = useState(() => {
    if (typeof window === "undefined") return true;
    const stored = localStorage.getItem("argus-theme");
    return stored ? stored === "dark" : true; /* dark is default */
  });

  useEffect(() => {
    const root = document.documentElement;
    if (dark) {
      root.classList.add("dark");
    } else {
      root.classList.remove("dark");
    }
    localStorage.setItem("argus-theme", dark ? "dark" : "light");
  }, [dark]);

  return (
    <button
      onClick={() => setDark(!dark)}
      className="bg-card shadow-[var(--neu-flat)] hover:shadow-[var(--neu-pressed)] rounded-xl p-2.5 text-muted-foreground hover:text-foreground transition-all duration-200"
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      title={dark ? "Switch to light mode" : "Switch to dark mode"}
    >
      {dark ? <Eye className="size-5" /> : <EyeOff className="size-5" />}
    </button>
  );
}

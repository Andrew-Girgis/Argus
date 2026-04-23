import { useState, type FormEvent } from "react";
import { Search, MapPin, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

interface SearchBarProps {
  onSearch: (lat: number, lon: number, address: string) => void;
  className?: string;
}

export default function SearchBar({ onSearch, className }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);

    const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
    if (!apiKey) {
      setError("Google Maps API key is not configured.");
      setLoading(false);
      return;
    }

    try {
      const encodedQuery = encodeURIComponent(query.trim());
      const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${encodedQuery}&key=${apiKey}`;
      const res = await fetch(url);
      const data = await res.json();

      if (data.status !== "OK" || !data.results || data.results.length === 0) {
        setError("Address not found. Please try a different search.");
        setLoading(false);
        return;
      }

      const result = data.results[0];
      const lat = result.geometry.location.lat as number;
      const lon = result.geometry.location.lng as number;
      const formattedAddress = result.formatted_address as string;

      onSearch(lat, lon, formattedAddress);
    } catch {
      setError("Failed to geocode address. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={cn("w-full max-w-2xl mx-auto", className)}>
      <form onSubmit={handleSubmit}>
        <div className="bg-card shadow-[var(--neu-flat)] focus-within:shadow-[var(--neu-pressed)] rounded-2xl px-5 py-4 flex items-center gap-3 transition-shadow duration-300">
          {loading ? (
            <Loader2 className="size-5 text-primary animate-spin" />
          ) : (
            <Search className="size-5 text-primary" />
          )}
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Enter an address, city, or postal code"
            disabled={loading}
            className="bg-transparent text-foreground placeholder:text-muted-foreground text-[15px] leading-relaxed font-sans outline-none flex-1 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="bg-surface-raised shadow-[var(--neu-flat)] hover:shadow-[var(--neu-pressed)] rounded-xl p-2.5 text-primary transition-shadow duration-200 disabled:opacity-30 disabled:pointer-events-none"
          >
            <MapPin className="size-5" />
          </button>
        </div>
      </form>
      {error && (
        <p className="mt-3 text-sm text-destructive text-center">{error}</p>
      )}
    </div>
  );
}

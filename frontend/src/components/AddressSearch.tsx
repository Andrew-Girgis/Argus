import { useState, type FormEvent } from "react";
import { MapPin, Search, Loader2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface AddressSearchProps {
  onSearch: (lat: number, lon: number, address: string) => void;
}

export default function AddressSearch({ onSearch }: AddressSearchProps) {
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
    <div className="w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="relative flex items-center gap-2">
        <div className="relative flex-1">
          <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Enter an address..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="h-12 pl-10 pr-4 text-base rounded-xl border-zinc-700 bg-zinc-900/50 focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:border-primary/50 transition-shadow"
            disabled={loading}
          />
        </div>
        <Button
          type="submit"
          size="lg"
          disabled={loading || !query.trim()}
          className="h-12 px-6 rounded-xl"
        >
          {loading ? <Loader2 className="size-4 animate-spin" /> : <Search className="size-4" />}
          <span className="ml-1.5">Search</span>
        </Button>
      </form>
      {error && <p className="mt-3 text-sm text-destructive text-center">{error}</p>}
    </div>
  );
}

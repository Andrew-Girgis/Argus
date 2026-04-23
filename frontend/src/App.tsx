import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { AlertCircle, Loader2 } from "lucide-react";
import { fetchProperty } from "@/lib/api";
import type { PropertyResponse } from "@/lib/types";
import ArgusLogo from "@/components/ArgusLogo";
import ThemeToggle from "@/components/ui/theme-toggle";
import SearchBar from "@/components/ui/search-bar";
import SectionHeader from "@/components/ui/section-header";
import PropertyHero from "@/components/PropertyHero";
import AIInsights from "@/components/AIInsights";
import MapPanel from "@/components/MapPanel";
import PropertySidebar from "@/components/PropertySidebar";
import JsonViewer from "@/components/JsonViewer";

export default function App() {
  const [address, setAddress] = useState("");
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);

  const mutation = useMutation<PropertyResponse, Error, { lat: number; lon: number }>({
    mutationFn: ({ lat, lon }) => fetchProperty(lat, lon),
  });

  function handleSearch(lat: number, lon: number, resolvedAddress: string) {
    setAddress(resolvedAddress);
    setCoords({ lat, lon });
    mutation.mutate({ lat, lon });
  }

  const property = mutation.data ?? null;
  const streetViewUrl =
    property?.images.find((img) => img.image_type === "street_view")?.url ?? null;
  const satelliteUrl = property?.images.find((img) => img.image_type === "satellite")?.url ?? null;

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Sticky Nav */}
      <nav className="sticky top-0 z-50 bg-background/80 backdrop-blur-xl border-b border-border">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <ArgusLogo className="size-8 text-primary" />
            <span className="font-heading text-lg font-bold tracking-tight text-foreground">
              Argus
            </span>
          </div>
          <ThemeToggle />
        </div>
      </nav>

      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {/* Hero Search — centered on load */}
        {!property && !mutation.isPending && !mutation.isError && (
          <div className="flex flex-col items-center justify-center py-20 gap-6">
            <div className="flex flex-col items-center gap-3">
              <ArgusLogo className="size-16 text-primary" />
              <h1 className="font-heading text-5xl font-bold tracking-tighter text-foreground">
                Argus
              </h1>
              <p className="text-muted-foreground text-lg leading-relaxed">
                Precision property intelligence
              </p>
            </div>
            <SearchBar onSearch={handleSearch} className="mt-4" />
          </div>
        )}

        {/* Compact search when results are showing */}
        {(property || mutation.isPending || mutation.isError) && (
          <div className="mb-8">
            <SearchBar onSearch={handleSearch} />
          </div>
        )}

        {/* Loading state — Panoptes scan animation */}
        {mutation.isPending && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <div className="relative">
              <div className="size-16 rounded-full border-2 border-primary/20" />
              <div className="absolute inset-0 size-16 rounded-full border-2 border-transparent border-t-primary animate-[argus-scan_1.5s_linear_infinite]" />
              <Loader2 className="absolute inset-0 m-auto size-6 text-primary animate-spin" />
            </div>
            <p className="text-sm text-muted-foreground font-medium">Analyzing property...</p>
          </div>
        )}

        {/* Error state */}
        {mutation.isError && (
          <div className="mx-auto max-w-lg rounded-2xl bg-card shadow-[var(--neu-flat)] p-6 text-center">
            <div className="flex items-center justify-center gap-2 text-destructive">
              <AlertCircle className="size-5" />
              <span className="font-heading font-semibold">Error</span>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {mutation.error.message || "Failed to fetch property data. Please try again."}
            </p>
          </div>
        )}

        {/* Results */}
        {property && coords && (
          <div className="space-y-8">
            {/* Hero images */}
            <PropertyHero
              streetViewUrl={streetViewUrl}
              satelliteUrl={satelliteUrl}
              address={address}
            />

            {/* Two-column: left data + right map */}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
              <div className="space-y-6 lg:col-span-2">
                <div>
                  <SectionHeader
                    title="AI Insights"
                    subtitle="AI-detected property attributes and confidence scores"
                  />
                  <div className="mt-4">
                    <AIInsights
                      analysis={property.analysis}
                      loading={false}
                      analysisId={property.analysis?.id ?? null}
                      propertyId={property.property.id ?? null}
                    />
                  </div>
                </div>

                <div>
                  <SectionHeader
                    title="Map"
                    subtitle="Property location and nearby points of interest"
                  />
                  <div className="mt-4">
                    <MapPanel
                      lat={coords.lat}
                      lon={coords.lon}
                    />
                  </div>
                </div>
              </div>

              <div className="lg:col-span-1">
                <PropertySidebar property={property} />
              </div>
            </div>

            {/* Raw JSON */}
            <JsonViewer data={property} title="Raw API Response" />
          </div>
        )}
      </div>
    </div>
  );
}

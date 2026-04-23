import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import SectionHeader from "@/components/ui/section-header";
import DataBadge from "@/components/ui/data-badge";
import type { PropertyResponse } from "@/lib/types";

interface PropertySidebarProps {
  property: PropertyResponse | null;
}

interface InfoRowProps {
  label: string;
  value: string | number | boolean | null | undefined;
  mono?: boolean;
}

function InfoRow({ label, value, mono = false }: InfoRowProps) {
  let displayValue: string;
  if (value === null || value === undefined) {
    displayValue = "N/A";
  } else if (typeof value === "boolean") {
    displayValue = value ? "Yes" : "No";
  } else {
    displayValue = String(value);
  }

  return (
    <div className="grid grid-cols-[1fr_1fr] gap-2 py-1.5">
      <dt className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        {label}
      </dt>
      <dd
        className={`text-sm font-medium text-foreground text-right ${mono ? "font-mono tracking-wider" : ""}`}
      >
        {displayValue}
      </dd>
    </div>
  );
}

export default function PropertySidebar({ property }: PropertySidebarProps) {
  if (!property) {
    return (
      <div className="flex h-full items-center justify-center rounded-2xl bg-card shadow-[var(--neu-flat)] p-6">
        <p className="text-sm text-muted-foreground">
          Search for an address to view property details
        </p>
      </div>
    );
  }

  const { property: prop, analysis } = property;

  return (
    <div className="rounded-2xl bg-card shadow-[var(--neu-flat)] overflow-hidden">
      <ScrollArea className="h-[700px]">
        <div className="p-5 space-y-5">
          {/* Location */}
          <div>
            <SectionHeader title="Location" />
            <dl className="mt-2">
              <InfoRow label="Address" value={prop.address} />
              <InfoRow label="Neighborhood" value={prop.neighborhood} />
              <InfoRow label="Cross Streets" value={prop.cross_streets} />
              <InfoRow
                label="Coordinates"
                value={`${prop.lat.toFixed(4)}, ${prop.lon.toFixed(4)}`}
                mono
              />
            </dl>
            <div className="mt-2">
              <DataBadge copyValue={`${prop.lat.toFixed(4)}, ${prop.lon.toFixed(4)}`}>
                {prop.lat.toFixed(4)}°N, {prop.lon.toFixed(4)}°W
              </DataBadge>
            </div>
          </div>

          <Separator className="bg-border" />

          {/* Property Details */}
          <div>
            <SectionHeader title="Property Details" />
            {analysis ? (
              <dl className="mt-2">
                <InfoRow label="Type" value={analysis.property_type} />
                <InfoRow label="Style" value={analysis.home_style} />
                <InfoRow label="Stories" value={analysis.stories} mono />
                <InfoRow label="Exterior" value={analysis.exterior_material} />
                <InfoRow label="Condition" value={analysis.condition_estimate} />
                <InfoRow label="Age" value={analysis.approximate_age} mono />
                <InfoRow label="Lot Shape" value={analysis.lot_shape} />
              </dl>
            ) : (
              <p className="mt-2 text-sm text-muted-foreground">No analysis available</p>
            )}
          </div>

          <Separator className="bg-border" />

          {/* Parking & Yard */}
          {analysis && (
            <>
              <div>
                <SectionHeader title="Parking & Yard" />
                <dl className="mt-2">
                  <InfoRow label="Parking" value={analysis.parking_type} />
                  <InfoRow label="Spaces" value={analysis.parking_spaces_estimate} mono />
                  <InfoRow label="Pool" value={analysis.has_pool} />
                  <InfoRow
                    label="Pool Confidence"
                    value={
                      analysis.pool_confidence != null
                        ? `${Math.round(analysis.pool_confidence * 100)}%`
                        : null
                    }
                    mono
                  />
                  <InfoRow label="Fenced Yard" value={analysis.has_fenced_yard} />
                  <InfoRow label="Trees" value={analysis.tree_count_estimate} mono />
                </dl>
              </div>

              <Separator className="bg-border" />
            </>
          )}

        </div>
      </ScrollArea>
    </div>
  );
}

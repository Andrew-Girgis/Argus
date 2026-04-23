import DataBadge from "@/components/ui/data-badge";

interface PropertyHeroProps {
  streetViewUrl: string | null;
  satelliteUrl: string | null;
  address: string;
}

function ImageSkeleton() {
  return <div className="aspect-video w-full animate-pulse rounded-2xl bg-surface-raised" />;
}

export default function PropertyHero({ streetViewUrl, satelliteUrl, address }: PropertyHeroProps) {
  return (
    <div className="w-full">
      <h2
        className="mb-4 font-heading text-xl font-semibold text-foreground truncate tracking-tight"
        title={address}
      >
        {address}
      </h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="relative overflow-hidden rounded-2xl shadow-[var(--neu-flat)]">
          {streetViewUrl ? (
            <img
              src={streetViewUrl}
              alt={`Street view of ${address}`}
              className="aspect-video w-full object-cover"
            />
          ) : (
            <ImageSkeleton />
          )}
          <DataBadge className="absolute bottom-3 left-3 bg-card/80 backdrop-blur-sm">
            Street View
          </DataBadge>
        </div>

        <div className="relative overflow-hidden rounded-2xl shadow-[var(--neu-flat)]">
          {satelliteUrl ? (
            <img
              src={satelliteUrl}
              alt={`Satellite view of ${address}`}
              className="aspect-video w-full object-cover"
            />
          ) : (
            <ImageSkeleton />
          )}
          <DataBadge className="absolute bottom-3 left-3 bg-card/80 backdrop-blur-sm">
            Satellite
          </DataBadge>
        </div>
      </div>
    </div>
  );
}

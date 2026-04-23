import { useEffect, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import DataBadge from "@/components/ui/data-badge";

const MARKER_COLOR = "#6366F1";

interface MapPanelProps {
  lat: number;
  lon: number;
}

export default function MapPanel({ lat, lon }: MapPanelProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const markerRef = useRef<mapboxgl.Marker | null>(null);

  useEffect(() => {
    if (!mapContainer.current) return;

    const token = import.meta.env.VITE_MAPBOX_API_KEY;
    if (!token) return;

    mapboxgl.accessToken = token;

    const map = new mapboxgl.Map({
      container: mapContainer.current,
      style: "mapbox://styles/mapbox/dark-v11",
      center: [lon, lat],
      zoom: 14,
    });

    markerRef.current = new mapboxgl.Marker({ color: MARKER_COLOR })
      .setLngLat([lon, lat])
      .addTo(map);

    return () => {
      markerRef.current?.remove();
      markerRef.current = null;
      map.remove();
    };
  }, [lat, lon]);

  const token = import.meta.env.VITE_MAPBOX_API_KEY;

  if (!token) {
    return (
      <div className="flex h-[400px] items-center justify-center rounded-2xl bg-card shadow-[var(--neu-flat)]">
        <p className="text-sm text-muted-foreground">Mapbox token not configured</p>
      </div>
    );
  }

  return (
    <div className="relative">
      <div
        ref={mapContainer}
        className="h-[400px] w-full rounded-2xl overflow-hidden shadow-[var(--neu-elevated)]"
      />
      {/* Coordinate badge — Panoptes data overlay */}
      <div className="absolute top-3 right-3">
        <DataBadge
          className="bg-card/95 backdrop-blur-xl"
          copyValue={`${lat.toFixed(4)}, ${lon.toFixed(4)}`}
        >
          {lat.toFixed(4)}°N, {lon.toFixed(4)}°W
        </DataBadge>
      </div>
    </div>
  );
}

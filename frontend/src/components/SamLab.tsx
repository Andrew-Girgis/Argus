import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Bot, Braces, Image as ImageIcon, Loader2, Play, Plus, Trash2 } from "lucide-react";
import { fetchImages, segmentImage } from "@/lib/api";
import type { SegmentPayload, SegmentResult, SegmentTarget } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import JsonViewer from "@/components/JsonViewer";
import SearchBar from "@/components/ui/search-bar";

const SATELLITE_TARGETS: SegmentTarget[] = [
  {
    type: "aerial_home_boundary",
    prompt:
      "the residential home directly under the map marker, including the full visible building footprint",
  },
  {
    type: "aerial_pool",
    prompt: "the swimming pool on the same residential property as the map marker",
  },
  {
    type: "aerial_driveway",
    prompt: "the driveway belonging to the residential home directly under the map marker",
  },
  {
    type: "aerial_roof",
    prompt: "the roof of the residential home directly under the map marker",
  },
];

const STREET_VIEW_TARGETS: SegmentTarget[] = [
  {
    type: "street_garage",
    prompt: "the garage door or garage structure of the home in focus only",
  },
];

export default function SamLab() {
  const [address, setAddress] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [satelliteUrl, setSatelliteUrl] = useState("");
  const [streetViewUrl, setStreetViewUrl] = useState("");
  const [imageType, setImageType] = useState<SegmentPayload["image_type"]>("satellite");
  const [satelliteZoom, setSatelliteZoom] = useState(20);
  const [guidanceMode, setGuidanceMode] = useState<"text" | "center_boxes">("center_boxes");
  const [lastCoordinates, setLastCoordinates] = useState<{ lat: number; lon: number } | null>(null);
  const [targets, setTargets] = useState<SegmentTarget[]>(SATELLITE_TARGETS);
  const [imageError, setImageError] = useState<string | null>(null);

  const imageMutation = useMutation({
    mutationFn: ({ lat, lon, zoom }: { lat: number; lon: number; zoom: number }) =>
      fetchImages(lat, lon, zoom),
  });

  const segmentMutation = useMutation<SegmentResult, Error, SegmentPayload>({
    mutationFn: segmentImage,
  });

  function switchImageType(nextType: SegmentPayload["image_type"]) {
    setImageType(nextType);
    setTargets(nextType === "satellite" ? SATELLITE_TARGETS : STREET_VIEW_TARGETS);
    setImageUrl(nextType === "satellite" ? satelliteUrl : streetViewUrl);
  }

  async function handleAddressSearch(lat: number, lon: number, resolvedAddress: string) {
    setAddress(resolvedAddress);
    setLastCoordinates({ lat, lon });
    setImageError(null);
    segmentMutation.reset();

    try {
      await fetchImagesForCoordinates(lat, lon, satelliteZoom, true);
    } catch (error) {
      setImageError(error instanceof Error ? error.message : "Failed to fetch imagery for SAM.");
    }
  }

  async function fetchImagesForCoordinates(
    lat: number,
    lon: number,
    zoom: number,
    runAfterFetch: boolean,
  ) {
    const images = await imageMutation.mutateAsync({ lat, lon, zoom });
    const nextSatelliteUrl = images.satellite.data?.url ?? "";
    const nextStreetViewUrl = images.street_view.data?.url ?? "";
    setSatelliteUrl(nextSatelliteUrl);
    setStreetViewUrl(nextStreetViewUrl);

    const selectedType = nextSatelliteUrl ? "satellite" : "street_view";
    const selectedUrl = nextSatelliteUrl || nextStreetViewUrl;
    if (!selectedUrl) {
      setImageError(
        images.satellite.error ||
          images.street_view.error ||
          "No Street View or satellite image was returned.",
      );
      return;
    }

    setImageType(selectedType);
    const selectedTargets = selectedType === "satellite" ? SATELLITE_TARGETS : STREET_VIEW_TARGETS;
    setTargets(selectedTargets);
    setImageUrl(selectedUrl);
    if (runAfterFetch) {
      runSegmentationFor(selectedUrl, selectedType, selectedTargets);
    }
  }

  async function refetchSatelliteAtZoom() {
    if (!lastCoordinates) return;
    setImageError(null);
    segmentMutation.reset();
    try {
      await fetchImagesForCoordinates(
        lastCoordinates.lat,
        lastCoordinates.lon,
        satelliteZoom,
        false,
      );
    } catch (error) {
      setImageError(error instanceof Error ? error.message : "Failed to refetch imagery for SAM.");
    }
  }

  function updateTarget(index: number, key: keyof SegmentTarget, value: string) {
    setTargets((current) =>
      current.map((target, targetIndex) =>
        targetIndex === index ? { ...target, [key]: value } : target,
      ),
    );
  }

  function addTarget() {
    setTargets((current) => [...current, { type: "custom_target", prompt: "" }]);
  }

  function removeTarget(index: number) {
    setTargets((current) => current.filter((_, targetIndex) => targetIndex !== index));
  }

  function runSegmentation() {
    runSegmentationFor(imageUrl, imageType, targets);
  }

  function runSegmentationFor(
    nextImageUrl: string,
    nextImageType: SegmentPayload["image_type"],
    nextTargets: SegmentTarget[],
  ) {
    segmentMutation.mutate({
      image_url: nextImageUrl,
      image_type: nextImageType,
      targets: nextTargets.filter((target) => target.type.trim() && target.prompt.trim()),
      guidance_mode: nextImageType === "satellite" ? guidanceMode : "text",
      center_box_scales:
        nextImageType === "satellite" && guidanceMode === "center_boxes"
          ? [0.12, 0.18, 0.26, 0.36, 0.5]
          : undefined,
    });
  }

  function handleImageUrlChange(nextUrl: string) {
    setImageUrl(nextUrl);
    if (nextUrl !== satelliteUrl && nextUrl !== streetViewUrl) {
      setAddress("");
    }
  }

  function selectFetchedImage(nextType: SegmentPayload["image_type"]) {
    switchImageType(nextType);
    const nextUrl = nextType === "satellite" ? satelliteUrl : streetViewUrl;
    if (nextUrl) {
      setImageUrl(nextUrl);
    }
  }

  function runCurrentFetchedImage(nextType: SegmentPayload["image_type"]) {
    const nextUrl = nextType === "satellite" ? satelliteUrl : streetViewUrl;
    const nextTargets = nextType === "satellite" ? SATELLITE_TARGETS : STREET_VIEW_TARGETS;
    if (!nextUrl) return;
    setImageType(nextType);
    setTargets(nextTargets);
    setImageUrl(nextUrl);
    runSegmentationFor(nextUrl, nextType, nextTargets);
  }

  const canRun = imageUrl.trim().length > 0 && targets.some((target) => target.prompt.trim());
  const resultStatus = getResultStatus(segmentMutation.data);

  return (
    <div className="space-y-6">
      <Card className="border border-border/60 bg-card/95">
        <CardHeader>
          <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Bot className="size-5 text-primary" />
                SAM 3.1 Segmentation Lab
              </CardTitle>
              <CardDescription>
                Search an address like Argus, fetch only imagery, then run SAM. No GPT/OpenAI call
                is made.
              </CardDescription>
            </div>
            {resultStatus && <Badge variant="outline">{resultStatus}</Badge>}
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="rounded-2xl border bg-background/50 p-4">
            <SearchBar onSearch={handleAddressSearch} />
            <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-center">
              <div className="w-full sm:w-40">
                <label
                  className="text-xs font-medium text-muted-foreground"
                  htmlFor="satellite-zoom"
                >
                  Satellite zoom
                </label>
                <Input
                  id="satellite-zoom"
                  type="number"
                  min={0}
                  max={21}
                  value={satelliteZoom}
                  onChange={(event) => setSatelliteZoom(Number(event.target.value))}
                />
              </div>
              <div className="w-full sm:w-52">
                <label
                  className="text-xs font-medium text-muted-foreground"
                  htmlFor="sam-guidance-mode"
                >
                  Satellite SAM mode
                </label>
                <select
                  id="sam-guidance-mode"
                  value={guidanceMode}
                  className="h-10 w-full rounded-lg border border-input bg-transparent px-3 text-sm outline-none transition-colors focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  onChange={(event) =>
                    setGuidanceMode(event.target.value as "text" | "center_boxes")
                  }
                >
                  <option value="center_boxes">Center guided boxes</option>
                  <option value="text">Text only</option>
                </select>
              </div>
              <Button
                type="button"
                variant="outline"
                disabled={!lastCoordinates || imageMutation.isPending}
                onClick={refetchSatelliteAtZoom}
              >
                Refetch at zoom
              </Button>
            </div>
            {address && (
              <p className="mt-3 text-center text-xs text-muted-foreground">
                SAM test address: <span className="font-medium text-foreground">{address}</span>
              </p>
            )}
            {imageError && (
              <p className="mt-3 text-center text-sm text-destructive">{imageError}</p>
            )}
          </div>

          <div className="grid gap-4 lg:grid-cols-[1fr_280px]">
            <div className="space-y-3">
              <label className="text-sm font-medium" htmlFor="sam-image-url">
                Image URL used for SAM
              </label>
              <Input
                id="sam-image-url"
                value={imageUrl}
                placeholder="https://maps.googleapis.com/... or any accessible image URL"
                onChange={(event) => handleImageUrlChange(event.target.value)}
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  type="button"
                  variant={imageType === "satellite" ? "default" : "outline"}
                  onClick={() => selectFetchedImage("satellite")}
                >
                  Satellite defaults
                </Button>
                <Button
                  type="button"
                  variant={imageType === "street_view" ? "default" : "outline"}
                  onClick={() => selectFetchedImage("street_view")}
                >
                  Street View defaults
                </Button>
              </div>
              {(satelliteUrl || streetViewUrl) && (
                <div className="flex flex-wrap gap-2 text-xs">
                  {satelliteUrl && (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => runCurrentFetchedImage("satellite")}
                    >
                      Run satellite SAM
                    </Button>
                  )}
                  {streetViewUrl && (
                    <Button
                      type="button"
                      size="sm"
                      variant="ghost"
                      onClick={() => runCurrentFetchedImage("street_view")}
                    >
                      Run street-view SAM
                    </Button>
                  )}
                </div>
              )}
            </div>

            <div className="overflow-hidden rounded-xl border bg-muted/30">
              {imageUrl ? (
                <img
                  src={imageUrl}
                  alt="SAM test input"
                  className="aspect-video h-full w-full object-cover"
                />
              ) : (
                <div className="flex aspect-video items-center justify-center gap-2 text-sm text-muted-foreground">
                  <ImageIcon className="size-4" />
                  Image preview
                </div>
              )}
            </div>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h3 className="font-heading text-sm font-semibold">Targets sent to SAM</h3>
                <p className="text-xs text-muted-foreground">
                  Edit the text prompts to test how specific language changes segmentation.
                </p>
              </div>
              <Button type="button" variant="outline" onClick={addTarget}>
                <Plus className="size-4" />
                Add target
              </Button>
            </div>

            <div className="space-y-3">
              {targets.map((target, index) => (
                <div
                  key={`${target.type}-${index}`}
                  className="rounded-xl border bg-background/60 p-3"
                >
                  <div className="grid gap-3 md:grid-cols-[220px_1fr_auto]">
                    <Input
                      aria-label="Target type"
                      value={target.type}
                      onChange={(event) => updateTarget(index, "type", event.target.value)}
                    />
                    <textarea
                      aria-label="Target prompt"
                      value={target.prompt}
                      rows={2}
                      className="min-h-16 w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm outline-none transition-colors placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                      onChange={(event) => updateTarget(index, "prompt", event.target.value)}
                    />
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      aria-label="Remove target"
                      onClick={() => removeTarget(index)}
                    >
                      <Trash2 className="size-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Braces className="size-4" />
              Search path: geocode in browser, fetch image URLs, then SAM only.
            </div>
            <Button
              type="button"
              disabled={!canRun || segmentMutation.isPending || imageMutation.isPending}
              onClick={runSegmentation}
            >
              {segmentMutation.isPending || imageMutation.isPending ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Play className="size-4" />
              )}
              Run SAM only
            </Button>
          </div>

          {segmentMutation.isError && (
            <div className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
              {segmentMutation.error.message}
            </div>
          )}
        </CardContent>
      </Card>

      {segmentMutation.data && <SegmentGallery result={segmentMutation.data} />}
      {segmentMutation.data && <JsonViewer data={segmentMutation.data} title="SAM Response" />}
    </div>
  );
}

function getResultStatus(result: SegmentResult | undefined) {
  if (!result) return null;
  const status = result.data?.status;
  return typeof status === "string" ? status : result.source;
}

function SegmentGallery({ result }: { result: SegmentResult }) {
  const segments = Array.isArray(result.data?.segments) ? result.data.segments : [];
  if (segments.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Segment Overlays</CardTitle>
        <CardDescription>Visual output returned by the SAM service.</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {segments.map((segment, index) => {
            if (!isSegmentPreview(segment)) return null;
            return (
              <div
                key={`${segment.type}-${index}`}
                className="overflow-hidden rounded-xl border bg-background"
              >
                <img
                  src={segment.overlay_png}
                  alt={`${segment.type} overlay`}
                  className="aspect-square w-full object-cover"
                />
                <div className="space-y-1 p-3 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-foreground">{segment.type}</span>
                    <Badge variant="outline">{segment.score.toFixed(2)}</Badge>
                  </div>
                  <p className="line-clamp-2 text-muted-foreground">{segment.prompt}</p>
                </div>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

function isSegmentPreview(value: unknown): value is {
  type: string;
  prompt: string;
  score: number;
  overlay_png: string;
} {
  return (
    typeof value === "object" &&
    value !== null &&
    "type" in value &&
    "prompt" in value &&
    "score" in value &&
    "overlay_png" in value &&
    typeof value.type === "string" &&
    typeof value.prompt === "string" &&
    typeof value.score === "number" &&
    typeof value.overlay_png === "string"
  );
}

import { useState } from "react";
import { submitFeedback } from "@/lib/api";
import {
  Home,
  Droplets,
  Trees,
  Car,
  ThumbsUp,
  Clock,
  Building2,
  Layers,
  BrickWall,
  Grid2x2Check,
  Shapes,
  RotateCw,
  Sun,
  Triangle,
  Footprints,
  RectangleHorizontal,
  Flame,
  Armchair,
  Waves,
  Warehouse,
  Wind,
} from "lucide-react";
import type { AIAnalysis } from "@/lib/types";
import type { ReactNode } from "react";

type FieldType = "boolean" | "enum" | "number" | "text";

interface FieldMeta {
  fieldName: string;
  fieldType: FieldType;
  options?: string[];
}

function yesNo(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return "Unsure";
  return value ? "Yes" : "No";
}

interface AIInsightsProps {
  analysis: AIAnalysis | null;
  loading: boolean;
  analysisId: string | null;
  propertyId: string | null;
}

interface InsightCardProps {
  icon: ReactNode;
  title: string;
  children: ReactNode;
  loading: boolean;
  confidence?: number | null;
  aiValue?: unknown;
  fieldMeta: FieldMeta;
  analysisId: string | null;
  propertyId: string | null;
}

const CARD_CLASSES =
  "absolute inset-0 flex flex-col gap-2 overflow-hidden rounded-2xl bg-card py-5 text-sm text-card-foreground shadow-[var(--neu-flat)] [backface-visibility:hidden]";

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color =
    value >= 0.8
      ? "from-primary to-accent"
      : value >= 0.6
        ? "from-warning to-warning"
        : "from-destructive to-destructive";

  return (
    <div className="w-full space-y-1.5">
      <div className="h-1.5 w-full rounded-full bg-background shadow-[var(--neu-pressed)]">
        <div
          className={`h-1.5 rounded-full bg-gradient-to-r ${color} shadow-[var(--neu-glow)] transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function CorrectionInput({
  fieldMeta,
  value,
  onChange,
}: {
  fieldMeta: FieldMeta;
  value: string;
  onChange: (v: string) => void;
}) {
  if (fieldMeta.fieldType === "boolean") {
    return (
      <div className="flex gap-1 w-full">
        {["true", "false", "null"].map((opt) => (
          <button
            key={opt}
            type="button"
            onClick={(e) => { e.stopPropagation(); onChange(opt); }}
            className={`flex-1 rounded-md py-1 text-xs font-medium transition-colors ${
              value === opt
                ? "bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground hover:text-foreground"
            }`}
          >
            {opt === "true" ? "Yes" : opt === "false" ? "No" : "Unsure"}
          </button>
        ))}
      </div>
    );
  }

  if (fieldMeta.fieldType === "enum" && fieldMeta.options) {
    return (
      <select
        value={value}
        onChange={(e) => { e.stopPropagation(); onChange(e.target.value); }}
        onClick={(e) => e.stopPropagation()}
        className="w-full rounded-md bg-background px-2 py-1 text-xs text-foreground border border-border focus:outline-none"
      >
        <option value="">Select…</option>
        {fieldMeta.options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    );
  }

  if (fieldMeta.fieldType === "number") {
    return (
      <input
        type="number"
        value={value}
        onChange={(e) => { e.stopPropagation(); onChange(e.target.value); }}
        onClick={(e) => e.stopPropagation()}
        className="w-full rounded-md bg-background px-2 py-1 text-xs text-foreground border border-border focus:outline-none"
        placeholder="Enter number"
      />
    );
  }

  return (
    <input
      type="text"
      value={value}
      onChange={(e) => { e.stopPropagation(); onChange(e.target.value); }}
      onClick={(e) => e.stopPropagation()}
      className="w-full rounded-md bg-background px-2 py-1 text-xs text-foreground border border-border focus:outline-none"
      placeholder="Correct value"
    />
  );
}

function InsightCard({ icon, title, children, loading, confidence, aiValue, fieldMeta, analysisId, propertyId }: InsightCardProps) {
  const [flipped, setFlipped] = useState(false);
  const [correcting, setCorrecting] = useState(false);
  const [correctedValue, setCorrectedValue] = useState<string>("");
  const [notes, setNotes] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.stopPropagation();
    e.preventDefault();
    setSubmitting(true);
    try {
      await submitFeedback({
        analysis_id: analysisId,
        property_id: propertyId,
        field_name: fieldMeta.fieldName,
        ai_value: aiValue,
        ai_confidence: confidence ?? null,
        corrected_value:
          fieldMeta.fieldType === "boolean"
            ? correctedValue === "true" ? true : correctedValue === "false" ? false : null
            : fieldMeta.fieldType === "number"
              ? Number(correctedValue)
              : correctedValue,
        notes: notes || undefined,
      });
      setSubmitted(true);
      setTimeout(() => {
        setSubmitted(false);
        setCorrecting(false);
        setFlipped(false);
      }, 1500);
    } catch {
      // silent — card stays open so user can retry
    } finally {
      setSubmitting(false);
    }
  }

  const hasConfidence = confidence != null;
  const pct = hasConfidence ? Math.round(confidence * 100) : null;
  const confidenceLabel =
    confidence == null ? null
    : confidence >= 0.8 ? "High confidence"
    : confidence >= 0.6 ? "Moderate confidence"
    : "Low confidence";

  return (
    <div
      className="relative h-[190px] [perspective:800px]"
      onClick={() => hasConfidence && !loading && setFlipped((f) => !f)}
      style={{ cursor: hasConfidence && !loading ? "pointer" : "default" }}
    >
      {/* Flip inner */}
      <div
        className="relative h-full w-full transition-transform duration-500 [transform-style:preserve-3d]"
        style={{ transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)" }}
      >
        {/* Front */}
        <div className={CARD_CLASSES}>
          <div className="flex items-start justify-between px-4">
            <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
              {icon}
              {title}
            </div>
            {hasConfidence && !loading && (
              <RotateCw className="size-3 shrink-0 text-muted-foreground/40 transition-colors group-hover:text-muted-foreground" />
            )}
          </div>
          <div className="px-4">
            {loading ? (
              <div className="h-7 w-28 animate-pulse rounded-lg bg-surface-raised" />
            ) : (
              <div className="font-heading text-xl font-semibold text-foreground">{children}</div>
            )}
          </div>
        </div>

        {/* Back */}
        <div
          className={`${CARD_CLASSES} [transform:rotateY(180deg)] justify-center gap-2 px-4`}
          onClick={(e) => correcting && e.stopPropagation()}
        >
          {submitted ? (
            <p className="text-xs font-semibold text-primary">Saved — thanks!</p>
          ) : correcting ? (
            <form onSubmit={handleSubmit} className="w-full space-y-2" onClick={(e) => e.stopPropagation()}>
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                Correct value
              </p>
              <CorrectionInput fieldMeta={fieldMeta} value={correctedValue} onChange={setCorrectedValue} />
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                onClick={(e) => e.stopPropagation()}
                placeholder="Notes (optional)"
                className="w-full rounded-md bg-background px-2 py-1 text-xs text-foreground border border-border focus:outline-none"
              />
              <div className="flex gap-1.5">
                <button
                  type="submit"
                  disabled={!correctedValue || submitting}
                  className="flex-1 rounded-md bg-primary py-1 text-xs font-semibold text-primary-foreground disabled:opacity-40"
                >
                  {submitting ? "Saving…" : "Submit"}
                </button>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setCorrecting(false); }}
                  className="flex-1 rounded-md bg-background py-1 text-xs font-medium text-muted-foreground border border-border"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <>
              <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
                AI Confidence
              </p>
              <p className="font-heading text-3xl font-bold text-foreground">{pct}%</p>
              <div className="w-full">
                {confidence != null && <ConfidenceBar value={confidence} />}
              </div>
              <p className="text-xs text-muted-foreground">{confidenceLabel}</p>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); setCorrecting(true); setCorrectedValue(""); setNotes(""); }}
                className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground transition-colors mt-1"
              >
                Correct this
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function AIInsights({ analysis, loading, analysisId, propertyId }: AIInsightsProps) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      <InsightCard
        icon={<Building2 className="size-4" />}
        title="Property Type"
        loading={loading}
        confidence={analysis?.property_type_confidence}
        aiValue={analysis?.property_type}
        fieldMeta={{ fieldName: "property_type", fieldType: "enum", options: ["Detached","Semi-Detached","Townhouse","Condo","Duplex","Triplex","Other"] }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {analysis?.property_type ?? "N/A"}
      </InsightCard>

      <InsightCard
        icon={<Home className="size-4" />}
        title="Style"
        loading={loading}
        confidence={analysis?.home_style_confidence}
        aiValue={analysis?.home_style}
        fieldMeta={{ fieldName: "home_style", fieldType: "text" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {analysis?.home_style ?? "N/A"}
      </InsightCard>

      <InsightCard
        icon={<Layers className="size-4" />}
        title="Stories"
        loading={loading}
        confidence={analysis?.stories_confidence}
        aiValue={analysis?.stories}
        fieldMeta={{ fieldName: "stories", fieldType: "enum", options: ["1","1.5","2","2.5","3","Split-level"] }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        <span className="font-mono">{analysis?.stories ?? "N/A"}</span>
      </InsightCard>

      <InsightCard
        icon={<BrickWall className="size-4" />}
        title="Exterior"
        loading={loading}
        confidence={analysis?.exterior_material_confidence}
        aiValue={analysis?.exterior_material}
        fieldMeta={{ fieldName: "exterior_material", fieldType: "enum", options: ["Brick","Vinyl Siding","Stone","Stucco","Wood","Aluminum","Mixed"] }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {analysis?.exterior_material ?? "N/A"}
      </InsightCard>

      <InsightCard
        icon={<Car className="size-4" />}
        title="Parking"
        loading={loading}
        confidence={analysis?.parking_type_confidence}
        aiValue={analysis?.parking_type}
        fieldMeta={{ fieldName: "parking_type", fieldType: "enum", options: ["Attached Garage","Detached Garage","Carport","Driveway Only","Street","None visible"] }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        <div className="flex flex-col">
          <span>{analysis?.parking_type ?? "N/A"}</span>
          {analysis?.parking_spaces_estimate != null && (
            <span className="font-mono text-xs text-muted-foreground">
              ~{analysis.parking_spaces_estimate} spaces
            </span>
          )}
        </div>
      </InsightCard>

      <InsightCard
        icon={<Droplets className="size-4" />}
        title="Pool"
        loading={loading}
        confidence={analysis?.pool_confidence}
        aiValue={analysis?.has_pool}
        fieldMeta={{ fieldName: "has_pool", fieldType: "boolean" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {yesNo(analysis?.has_pool)}
      </InsightCard>

      <InsightCard
        icon={<Trees className="size-4" />}
        title="Trees"
        loading={loading}
        confidence={analysis?.tree_count_confidence}
        aiValue={analysis?.tree_count_estimate}
        fieldMeta={{ fieldName: "tree_count_estimate", fieldType: "number" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        <span className="font-mono">{analysis?.tree_count_estimate ?? "N/A"}</span>
      </InsightCard>

      <InsightCard
        icon={<Grid2x2Check className="size-4" />}
        title="Fenced Yard"
        loading={loading}
        confidence={analysis?.fence_confidence}
        aiValue={analysis?.has_fenced_yard}
        fieldMeta={{ fieldName: "has_fenced_yard", fieldType: "boolean" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {yesNo(analysis?.has_fenced_yard)}
      </InsightCard>

      <InsightCard
        icon={<Shapes className="size-4" />}
        title="Lot Shape"
        loading={loading}
        confidence={analysis?.lot_shape_confidence}
        aiValue={analysis?.lot_shape}
        fieldMeta={{ fieldName: "lot_shape", fieldType: "enum", options: ["Regular","Pie-Shaped","Corner","Irregular","Cul-de-sac"] }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {analysis?.lot_shape ?? "N/A"}
      </InsightCard>

      <InsightCard
        icon={<ThumbsUp className="size-4" />}
        title="Condition"
        loading={loading}
        confidence={analysis?.condition_confidence}
        aiValue={analysis?.condition_estimate}
        fieldMeta={{ fieldName: "condition_estimate", fieldType: "enum", options: ["Excellent","Good","Fair","Poor"] }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {analysis?.condition_estimate ?? "N/A"}
      </InsightCard>

      <InsightCard
        icon={<Clock className="size-4" />}
        title="Age"
        loading={loading}
        confidence={analysis?.approximate_age_confidence}
        aiValue={analysis?.approximate_age}
        fieldMeta={{ fieldName: "approximate_age", fieldType: "enum", options: ["0-5 years","5-15 years","16-30 years","30-50 years","50+ years"] }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        <span className="font-mono">{analysis?.approximate_age ?? "N/A"}</span>
      </InsightCard>

      <InsightCard
        icon={<Sun className="size-4" />}
        title="Solar Panels"
        loading={loading}
        confidence={analysis?.solar_panels_confidence}
        aiValue={analysis?.has_solar_panels}
        fieldMeta={{ fieldName: "has_solar_panels", fieldType: "boolean" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {yesNo(analysis?.has_solar_panels)}
      </InsightCard>

      <InsightCard
        icon={<Triangle className="size-4" />}
        title="Roof Type"
        loading={loading}
        confidence={analysis?.roof_type_confidence}
        aiValue={analysis?.roof_type}
        fieldMeta={{ fieldName: "roof_type", fieldType: "enum", options: ["Gable","Clipped Gable","Dutch Gable","Gambrel","Hip","Mansard","Shed","Flat"] }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {analysis?.roof_type ?? "N/A"}
      </InsightCard>

      <InsightCard
        icon={<Footprints className="size-4" />}
        title="Sidewalk"
        loading={loading}
        confidence={analysis?.sidewalk_confidence}
        aiValue={analysis?.has_sidewalk}
        fieldMeta={{ fieldName: "has_sidewalk", fieldType: "boolean" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {yesNo(analysis?.has_sidewalk)}
      </InsightCard>

      <InsightCard
        icon={<RectangleHorizontal className="size-4" />}
        title="Driveway"
        loading={loading}
        confidence={analysis?.driveway_material_confidence}
        aiValue={analysis?.driveway_material}
        fieldMeta={{ fieldName: "driveway_material", fieldType: "enum", options: ["Concrete","Asphalt","Interlock/Paving Stone","Gravel","None visible"] }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {analysis?.driveway_material ?? "N/A"}
      </InsightCard>

      <InsightCard
        icon={<Flame className="size-4" />}
        title="Chimney"
        loading={loading}
        confidence={analysis?.chimney_confidence}
        aiValue={analysis?.has_chimney}
        fieldMeta={{ fieldName: "has_chimney", fieldType: "boolean" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {yesNo(analysis?.has_chimney)}
      </InsightCard>

      <InsightCard
        icon={<Armchair className="size-4" />}
        title="Deck / Patio"
        loading={loading}
        confidence={analysis?.deck_patio_confidence}
        aiValue={analysis?.has_deck_or_patio}
        fieldMeta={{ fieldName: "has_deck_or_patio", fieldType: "boolean" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {yesNo(analysis?.has_deck_or_patio)}
      </InsightCard>

      <InsightCard
        icon={<Waves className="size-4" />}
        title="Gutters"
        loading={loading}
        confidence={analysis?.gutters_confidence}
        aiValue={analysis?.has_gutters}
        fieldMeta={{ fieldName: "has_gutters", fieldType: "boolean" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {yesNo(analysis?.has_gutters)}
      </InsightCard>

      <InsightCard
        icon={<Warehouse className="size-4" />}
        title="Shed / Structure"
        loading={loading}
        confidence={analysis?.detached_structure_confidence}
        aiValue={analysis?.has_detached_structure}
        fieldMeta={{ fieldName: "has_detached_structure", fieldType: "boolean" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {yesNo(analysis?.has_detached_structure)}
      </InsightCard>

      <InsightCard
        icon={<Wind className="size-4" />}
        title="AC Unit"
        loading={loading}
        confidence={analysis?.ac_unit_confidence}
        aiValue={analysis?.has_ac_unit}
        fieldMeta={{ fieldName: "has_ac_unit", fieldType: "boolean" }}
        analysisId={analysisId}
        propertyId={propertyId}
      >
        {yesNo(analysis?.has_ac_unit)}
      </InsightCard>
    </div>
  );
}

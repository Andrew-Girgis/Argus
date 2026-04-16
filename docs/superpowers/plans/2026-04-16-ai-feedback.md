# AI Feedback System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to correct individual AI insight card values in-context, persisting corrections to Supabase for future prompt refinement or fine-tuning.

**Architecture:** A third "correction" state is added to each flippable insight card (front → confidence back → correction form). Corrections are posted to a new `POST /api/v1/feedback` endpoint, saved to a new `ai_feedback` Supabase table. The card knows its field name, field type, and the valid enum options so the correction input is always appropriate to the data.

**Tech Stack:** FastAPI (backend), React + TanStack Query (frontend), Supabase (PostgreSQL), TypeScript

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `backend/app/services/feedback.py` | Create | Insert feedback record into Supabase |
| `backend/app/routes/feedback.py` | Create | `POST /api/v1/feedback` endpoint |
| `backend/app/models/schemas.py` | Modify | Add `FeedbackRequest` schema |
| `backend/app/main.py` | Modify | Register feedback router |
| `frontend/src/lib/api.ts` | Modify | Add `submitFeedback()` call |
| `frontend/src/lib/types.ts` | Modify | Add `FeedbackPayload` type |
| `frontend/src/components/AIInsights.tsx` | Modify | Add correction state + form to `InsightCard` |

---

### Task 1: Supabase table

**Files:**
- No code file — SQL to run in Supabase dashboard

- [ ] **Step 1: Create the `ai_feedback` table in Supabase**

Open the Supabase SQL editor and run:

```sql
create table ai_feedback (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid references ai_analysis(id) on delete set null,
  property_id uuid references properties(id) on delete set null,
  field_name text not null,
  ai_value jsonb,
  ai_confidence double precision,
  corrected_value jsonb not null,
  notes text,
  submitted_at timestamptz not null default now()
);
```

- [ ] **Step 2: Verify table exists**

In the Supabase Table Editor, confirm `ai_feedback` appears with the correct columns.

---

### Task 2: Backend schema

**Files:**
- Modify: `backend/app/models/schemas.py`

- [ ] **Step 1: Add `FeedbackRequest` to schemas**

Open `backend/app/models/schemas.py`. After the `ServiceResult` class, add:

```python
class FeedbackRequest(BaseModel):
    analysis_id: str | None = None
    property_id: str | None = None
    field_name: str
    ai_value: Any = None
    ai_confidence: float | None = None
    corrected_value: Any
    notes: str | None = None
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/models/schemas.py
git commit -m "feat: add FeedbackRequest schema"
```

---

### Task 3: Feedback service

**Files:**
- Create: `backend/app/services/feedback.py`

- [ ] **Step 1: Create the service file**

Create `backend/app/services/feedback.py`:

```python
import logging
from datetime import datetime, timezone
from uuid import uuid4

from app.models.schemas import FeedbackRequest, ServiceResult

logger = logging.getLogger(__name__)


async def save_feedback(req: FeedbackRequest) -> ServiceResult:
    """Save a user correction to the ai_feedback table."""
    try:
        from app.services.supabase import _get_client
        client = _get_client()
        record = {
            "id": str(uuid4()),
            "analysis_id": req.analysis_id,
            "property_id": req.property_id,
            "field_name": req.field_name,
            "ai_value": req.ai_value,
            "ai_confidence": req.ai_confidence,
            "corrected_value": req.corrected_value,
            "notes": req.notes,
            "submitted_at": datetime.now(timezone.utc).isoformat(),
        }
        result = client.table("ai_feedback").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving feedback to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")
```

- [ ] **Step 2: Commit**

```bash
git add backend/app/services/feedback.py
git commit -m "feat: add feedback service"
```

---

### Task 4: Feedback route

**Files:**
- Create: `backend/app/routes/feedback.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the route file**

Create `backend/app/routes/feedback.py`:

```python
import logging

from fastapi import APIRouter

from app.models.schemas import FeedbackRequest
from app.services import feedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


@router.post("")
async def submit_feedback(req: FeedbackRequest):
    """Save a user correction for an AI-generated field."""
    result = await feedback.save_feedback(req)
    if result.error:
        logger.warning("Feedback save failed: %s", result.error)
    return {"ok": result.error is None, "error": result.error}
```

- [ ] **Step 2: Read `backend/app/main.py` to find where routers are registered**

```bash
cat backend/app/main.py
```

- [ ] **Step 3: Register the feedback router in `main.py`**

Add the import and `app.include_router` call alongside the existing property router. The exact lines depend on what you see in Step 2, but the pattern is:

```python
from app.routes import feedback as feedback_router
app.include_router(feedback_router.router)
```

- [ ] **Step 4: Verify the endpoint appears in API docs**

Start the backend (`cd backend && uv run uvicorn app.main:app --reload`) and open `http://localhost:8000/docs`. Confirm `POST /api/v1/feedback` is listed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routes/feedback.py backend/app/main.py
git commit -m "feat: add POST /api/v1/feedback endpoint"
```

---

### Task 5: Frontend types and API call

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Modify: `frontend/src/lib/api.ts`

- [ ] **Step 1: Add `FeedbackPayload` to `frontend/src/lib/types.ts`**

At the end of the file, add:

```typescript
export interface FeedbackPayload {
  analysis_id: string | null;
  property_id: string | null;
  field_name: string;
  ai_value: unknown;
  ai_confidence: number | null;
  corrected_value: unknown;
  notes?: string;
}
```

- [ ] **Step 2: Read `frontend/src/lib/api.ts` to find the base URL pattern**

```bash
cat frontend/src/lib/api.ts
```

- [ ] **Step 3: Add `submitFeedback` to `frontend/src/lib/api.ts`**

Following the same fetch pattern already in the file, add:

```typescript
import type { FeedbackPayload } from "@/lib/types";

export async function submitFeedback(payload: FeedbackPayload): Promise<{ ok: boolean }> {
  const res = await fetch(`${API_BASE}/api/v1/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to submit feedback");
  return res.json();
}
```

(`API_BASE` is whatever constant is already used in `api.ts` for the backend URL.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/lib/api.ts
git commit -m "feat: add FeedbackPayload type and submitFeedback API call"
```

---

### Task 6: InsightCard field metadata

**Files:**
- Modify: `frontend/src/components/AIInsights.tsx`

This task adds the field metadata to each card so the correction form knows what input type to render. No UI changes yet — just plumbing.

- [ ] **Step 1: Define field types at the top of `AIInsights.tsx`**

After the imports, before the `yesNo` helper, add:

```typescript
type FieldType = "boolean" | "enum" | "number" | "text";

interface FieldMeta {
  fieldName: string;
  fieldType: FieldType;
  options?: string[]; // for enum fields
}
```

- [ ] **Step 2: Add `fieldMeta` and `analysisId` / `propertyId` to `InsightCardProps`**

Update the `InsightCardProps` interface:

```typescript
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
```

- [ ] **Step 3: Update `InsightCard` function signature to accept new props**

```typescript
function InsightCard({
  icon,
  title,
  children,
  loading,
  confidence,
  aiValue,
  fieldMeta,
  analysisId,
  propertyId,
}: InsightCardProps) {
```

Leave the body unchanged for now — the new props are just threaded through.

- [ ] **Step 4: Pass `fieldMeta`, `analysisId`, `propertyId`, and `aiValue` to every `InsightCard` in the JSX**

For each of the 20 cards, add the four new props. Examples:

```tsx
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
```

Full `fieldMeta` values for all 20 cards:

| Card | fieldName | fieldType | options |
|---|---|---|---|
| Property Type | `property_type` | enum | Detached, Semi-Detached, Townhouse, Condo, Duplex, Triplex, Other |
| Style | `home_style` | text | — |
| Stories | `stories` | enum | 1, 1.5, 2, 2.5, 3, Split-level |
| Exterior | `exterior_material` | enum | Brick, Vinyl Siding, Stone, Stucco, Wood, Aluminum, Mixed |
| Parking | `parking_type` | enum | Attached Garage, Detached Garage, Carport, Driveway Only, Street, None visible |
| Pool | `has_pool` | boolean | — |
| Trees | `tree_count_estimate` | number | — |
| Fenced Yard | `has_fenced_yard` | boolean | — |
| Lot Shape | `lot_shape` | enum | Regular, Pie-Shaped, Corner, Irregular, Cul-de-sac |
| Condition | `condition_estimate` | enum | Excellent, Good, Fair, Poor |
| Age | `approximate_age` | enum | 0-5 years, 5-15 years, 16-30 years, 30-50 years, 50+ years |
| Solar Panels | `has_solar_panels` | boolean | — |
| Roof Type | `roof_type` | enum | Gable, Clipped Gable, Dutch Gable, Gambrel, Hip, Mansard, Shed, Flat |
| Sidewalk | `has_sidewalk` | boolean | — |
| Driveway | `driveway_material` | enum | Concrete, Asphalt, Interlock/Paving Stone, Gravel, None visible |
| Chimney | `has_chimney` | boolean | — |
| Deck / Patio | `has_deck_or_patio` | boolean | — |
| Gutters | `has_gutters` | boolean | — |
| Shed / Structure | `has_detached_structure` | boolean | — |
| AC Unit | `has_ac_unit` | boolean | — |

- [ ] **Step 5: Update `AIInsights` to accept and pass `analysisId` and `propertyId`**

```typescript
interface AIInsightsProps {
  analysis: AIAnalysis | null;
  loading: boolean;
  analysisId: string | null;
  propertyId: string | null;
}

export default function AIInsights({ analysis, loading, analysisId, propertyId }: AIInsightsProps) {
```

- [ ] **Step 6: Pass `analysisId` and `propertyId` from `App.tsx` into `<AIInsights />`**

In `App.tsx`, the `property` object has `property.analysis.id` and `property.property.id`. Thread them down:

```tsx
<AIInsights
  analysis={property.analysis}
  loading={false}
  analysisId={property.analysis?.id ?? null}
  propertyId={property.property.id ?? null}
/>
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/AIInsights.tsx frontend/src/App.tsx
git commit -m "feat: add field metadata and IDs to InsightCard"
```

---

### Task 7: Correction form UI

**Files:**
- Modify: `frontend/src/components/AIInsights.tsx`

This task adds the third card state: a correction form on the back face, accessible via a "Correct this" button.

- [ ] **Step 1: Add correction state and mutation to `InsightCard`**

Inside `InsightCard`, add below the existing `useState`:

```typescript
const [correcting, setCorrecting] = useState(false);
const [correctedValue, setCorrectedValue] = useState<string>("");
const [notes, setNotes] = useState("");
const [submitted, setSubmitted] = useState(false);
const [submitting, setSubmitting] = useState(false);
```

- [ ] **Step 2: Add the `handleSubmit` function inside `InsightCard`**

```typescript
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
      corrected_value: fieldMeta.fieldType === "boolean"
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
```

Add the import at the top of the file:

```typescript
import { submitFeedback } from "@/lib/api";
```

- [ ] **Step 3: Build the correction input component**

Add this helper inside `AIInsights.tsx` (above `InsightCard`):

```typescript
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
            className={`flex-1 rounded-md py-1 text-xs font-medium transition-colors
              ${value === opt
                ? "bg-primary text-primary-foreground"
                : "bg-background text-muted-foreground hover:text-foreground"}`}
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
```

- [ ] **Step 4: Replace the back face JSX with the three-state version**

Replace the entire back face `<div>` in `InsightCard` with:

```tsx
{/* Back */}
<div
  className={`${CARD_CLASSES} [transform:rotateY(180deg)] justify-center gap-2 px-4`}
  onClick={(e) => e.stopPropagation()}
>
  {submitted ? (
    <p className="text-xs font-semibold text-primary">Saved — thanks!</p>
  ) : correcting ? (
    <form onSubmit={handleSubmit} className="w-full space-y-2" onClick={(e) => e.stopPropagation()}>
      <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
        Correct value
      </p>
      <CorrectionInput
        fieldMeta={fieldMeta}
        value={correctedValue}
        onChange={setCorrectedValue}
      />
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
```

- [ ] **Step 5: Verify in browser**

1. Search for any address
2. Click an insight card — it flips to show confidence + "Correct this"
3. Click "Correct this" — form appears with appropriate input type
4. Submit a correction — "Saved — thanks!" appears, card flips back after 1.5s
5. Open Supabase Table Editor → `ai_feedback` — confirm the row was inserted with correct field values

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/AIInsights.tsx frontend/src/lib/api.ts
git commit -m "feat: add inline correction form to AI insight cards"
```

---

## Done

All corrections are now captured in `ai_feedback` with:
- The field that was wrong (`field_name`)
- What the AI said (`ai_value`) and how confident it was (`ai_confidence`)
- What the correct value is (`corrected_value`)
- Optional notes from the user

**Future training use:** Query `ai_feedback` joined to `ai_analysis` (for `raw_response` containing the full AI output) and `property_images` (for the image URLs). Export as OpenAI fine-tuning JSONL with the images + prompt as user content and the corrected field value in the assistant response.

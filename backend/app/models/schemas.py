from datetime import datetime
from enum import Enum
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


# --- Enums ---


class ImageType(str, Enum):
    STREET_VIEW = "street_view"
    SATELLITE = "satellite"


# --- Database models ---


class Property(BaseModel):
    id: UUID
    address: str
    lat: float
    lon: float
    neighborhood: str | None = None
    cross_streets: str | None = None
    created_at: datetime
    updated_at: datetime


class PropertyImage(BaseModel):
    id: UUID
    property_id: UUID
    image_type: ImageType
    url: str
    fetched_at: datetime


Confidence = Annotated[
    float,
    Field(
        ge=0.0,
        le=1.0,
        description="Certainty from 0.0 to 1.0 based on what is visible. "
        "1.0 only when unambiguous; 0.0 when the value is null.",
    ),
]

PropertyType = Literal[
    "Detached", "Semi-Detached", "Townhouse", "Condo", "Duplex", "Triplex", "Other"
]
Stories = Literal["1", "1.5", "2", "2.5", "3", "Split-level"]
ParkingType = Literal[
    "Attached Garage",
    "Detached Garage",
    "Carport",
    "Driveway Only",
    "Street",
    "None visible",
]
Condition = Literal["Excellent", "Good", "Fair", "Poor"]
ApproximateAge = Literal[
    "0-5 years", "5-15 years", "16-30 years", "30-50 years", "50+ years"
]
LotShape = Literal["Regular", "Pie-Shaped", "Corner", "Irregular", "Cul-de-sac"]
RoofType = Literal[
    "Gable", "Clipped Gable", "Dutch Gable", "Gambrel", "Hip", "Mansard", "Shed", "Flat"
]
DrivewayMaterial = Literal[
    "Concrete", "Asphalt", "Interlock/Paving Stone", "Gravel", "None visible"
]


class PropertyAnalysis(BaseModel):
    """Vision model output: one value and one confidence per observed feature.

    Every value is nullable. ``None`` means the model could not determine the
    value from the images, which is different from ``False`` or ``0``. This
    model is also the Structured Outputs schema sent to OpenAI, so field
    descriptions are part of the prompt.
    """

    property_type: PropertyType | None = None
    property_type_confidence: Confidence = 0.0
    home_style: str | None = Field(
        default=None,
        description="Architectural style, e.g. Colonial, Ranch, Tudor, Split-level, "
        "Modern, Victorian, Bungalow, Contemporary.",
    )
    home_style_confidence: Confidence = 0.0
    stories: Stories | None = None
    stories_confidence: Confidence = 0.0
    exterior_material: str | None = Field(
        default=None,
        description="Primary exterior material, e.g. Brick, Vinyl Siding, Stone, "
        "Stucco, Wood, Aluminum, Mixed.",
    )
    exterior_material_confidence: Confidence = 0.0
    has_pool: bool | None = None
    pool_confidence: Confidence = 0.0
    tree_count_estimate: int | None = Field(default=None, ge=0)
    tree_count_confidence: Confidence = 0.0
    has_garage: bool | None = None
    garage_confidence: Confidence = 0.0
    parking_type: ParkingType | None = None
    parking_type_confidence: Confidence = 0.0
    parking_spaces_estimate: int | None = Field(default=None, ge=0)
    parking_spaces_confidence: Confidence = 0.0
    condition_estimate: Condition | None = None
    condition_confidence: Confidence = 0.0
    approximate_age: ApproximateAge | None = None
    approximate_age_confidence: Confidence = 0.0
    lot_shape: LotShape | None = None
    lot_shape_confidence: Confidence = 0.0
    has_fenced_yard: bool | None = None
    fence_confidence: Confidence = 0.0
    has_solar_panels: bool | None = None
    solar_panels_confidence: Confidence = 0.0
    roof_type: RoofType | None = None
    roof_type_confidence: Confidence = 0.0
    has_sidewalk: bool | None = None
    sidewalk_confidence: Confidence = 0.0
    driveway_material: DrivewayMaterial | None = None
    driveway_material_confidence: Confidence = 0.0
    has_chimney: bool | None = None
    chimney_confidence: Confidence = 0.0
    has_deck_or_patio: bool | None = None
    deck_patio_confidence: Confidence = 0.0
    has_gutters: bool | None = None
    gutters_confidence: Confidence = 0.0
    has_detached_structure: bool | None = Field(
        default=None,
        description="Sheds, workshops, or secondary structures, excluding the main garage.",
    )
    detached_structure_confidence: Confidence = 0.0
    has_ac_unit: bool | None = None
    ac_unit_confidence: Confidence = 0.0

    def to_record(
        self,
        *,
        analysis_id: str,
        property_id: str,
        model_used: str,
        analyzed_at: str,
    ) -> dict[str, Any]:
        """Build the ``ai_analysis`` row, also used as the API response."""
        return {
            "id": analysis_id,
            "property_id": property_id,
            "model_used": model_used,
            **self.model_dump(include=set(PropertyAnalysis.model_fields)),
            "raw_response": self.model_dump(),
            "analyzed_at": analyzed_at,
        }


class AIAnalysis(PropertyAnalysis):
    id: UUID
    property_id: UUID
    model_used: str
    raw_response: dict[str, Any] = Field(default_factory=dict)
    analyzed_at: datetime


class GeospatialData(BaseModel):
    id: UUID
    property_id: UUID
    pois: list[Any] = Field(default_factory=list)
    fetched_at: datetime


# --- Request / Response models ---


class PropertyRequest(BaseModel):
    lat: float
    lon: float


class AnalyzeRequest(BaseModel):
    street_view_url: str
    satellite_url: str


class ServiceResult(BaseModel):
    data: Any = None
    error: str | None = None
    source: str = ""


class FeedbackRequest(BaseModel):
    analysis_id: str | None = None
    property_id: str | None = None
    field_name: str
    ai_value: Any = None
    ai_confidence: float | None = None
    corrected_value: Any
    notes: str | None = None


class PropertyResponse(BaseModel):
    property: Property | None = None
    images: list[PropertyImage] = Field(default_factory=list)
    analysis: AIAnalysis | None = None
    geospatial: GeospatialData | None = None
    errors: list[str] = Field(default_factory=list)

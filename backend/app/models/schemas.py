from datetime import datetime
from enum import Enum
from typing import Any
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


class AIAnalysis(BaseModel):
    id: UUID
    property_id: UUID
    model_used: str
    property_type: str | None = None
    property_type_confidence: float | None = None
    home_style: str | None = None
    home_style_confidence: float | None = None
    stories: str | None = None
    stories_confidence: float | None = None
    exterior_material: str | None = None
    exterior_material_confidence: float | None = None
    has_pool: bool | None = None
    pool_confidence: float | None = None
    tree_count_estimate: int | None = None
    tree_count_confidence: float | None = None
    has_garage: bool | None = None
    garage_confidence: float | None = None
    parking_type: str | None = None
    parking_type_confidence: float | None = None
    parking_spaces_estimate: int | None = None
    parking_spaces_confidence: float | None = None
    condition_estimate: str | None = None
    condition_confidence: float | None = None
    approximate_age: str | None = None
    approximate_age_confidence: float | None = None
    lot_shape: str | None = None
    lot_shape_confidence: float | None = None
    has_fenced_yard: bool | None = None
    fence_confidence: float | None = None
    has_solar_panels: bool | None = None
    solar_panels_confidence: float | None = None
    roof_type: str | None = None
    roof_type_confidence: float | None = None
    has_sidewalk: bool | None = None
    sidewalk_confidence: float | None = None
    driveway_material: str | None = None
    driveway_material_confidence: float | None = None
    has_chimney: bool | None = None
    chimney_confidence: float | None = None
    has_deck_or_patio: bool | None = None
    deck_patio_confidence: float | None = None
    has_gutters: bool | None = None
    gutters_confidence: float | None = None
    has_detached_structure: bool | None = None
    detached_structure_confidence: float | None = None
    has_ac_unit: bool | None = None
    ac_unit_confidence: float | None = None
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

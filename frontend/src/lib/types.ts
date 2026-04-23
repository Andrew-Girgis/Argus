export interface Property {
  id: string;
  address: string;
  lat: number;
  lon: number;
  neighborhood: string | null;
  cross_streets: string | null;
  created_at: string;
  updated_at: string;
}

export interface PropertyImage {
  id: string;
  property_id: string;
  image_type: "street_view" | "satellite";
  url: string;
  fetched_at: string;
}

export interface AIAnalysis {
  id: string;
  property_id: string;
  model_used: string;
  property_type: string | null;
  property_type_confidence: number | null;
  home_style: string | null;
  home_style_confidence: number | null;
  stories: string | null;
  stories_confidence: number | null;
  exterior_material: string | null;
  exterior_material_confidence: number | null;
  has_pool: boolean;
  pool_confidence: number | null;
  tree_count_estimate: number | null;
  tree_count_confidence: number | null;
  has_garage: boolean;
  garage_confidence: number | null;
  parking_type: string | null;
  parking_type_confidence: number | null;
  parking_spaces_estimate: number | null;
  parking_spaces_confidence: number | null;
  condition_estimate: string | null;
  condition_confidence: number | null;
  approximate_age: string | null;
  approximate_age_confidence: number | null;
  lot_shape: string | null;
  lot_shape_confidence: number | null;
  has_fenced_yard: boolean | null;
  fence_confidence: number | null;
  has_solar_panels: boolean | null;
  solar_panels_confidence: number | null;
  roof_type: string | null;
  roof_type_confidence: number | null;
  has_sidewalk: boolean | null;
  sidewalk_confidence: number | null;
  driveway_material: string | null;
  driveway_material_confidence: number | null;
  has_chimney: boolean | null;
  chimney_confidence: number | null;
  has_deck_or_patio: boolean | null;
  deck_patio_confidence: number | null;
  has_gutters: boolean | null;
  gutters_confidence: number | null;
  has_detached_structure: boolean | null;
  detached_structure_confidence: number | null;
  has_ac_unit: boolean | null;
  ac_unit_confidence: number | null;
  raw_response: Record<string, unknown>;
  analyzed_at: string;
}

export interface POI {
  name: string;
  category: string;
  lat: number;
  lon: number;
  distance_m?: number;
}

export interface GeospatialData {
  id: string;
  property_id: string;
  pois: POI[];
  fetched_at: string;
}

export interface PropertyResponse {
  property: Property;
  images: PropertyImage[];
  analysis: AIAnalysis | null;
  segmentation: Record<string, unknown> | null;
  geospatial: GeospatialData | null;
}

export interface ServiceResult<T = unknown> {
  data: T | null;
  error: string | null;
  source: string;
}

export interface FeedbackPayload {
  analysis_id: string | null;
  property_id: string | null;
  field_name: string;
  ai_value: unknown;
  ai_confidence: number | null;
  corrected_value: unknown;
  notes?: string;
}

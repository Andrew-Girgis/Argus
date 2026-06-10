CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS properties (
    id UUID PRIMARY KEY,
    canonical_address TEXT NOT NULL,
    address_hash TEXT UNIQUE NOT NULL,
    normalized_components JSONB NOT NULL DEFAULT '{}'::jsonb,
    display_address TEXT NOT NULL,
    country TEXT,
    province_state TEXT,
    municipality TEXT,
    city TEXT,
    postal_code TEXT,
    neighborhood TEXT,
    cross_streets TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    google_place_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS property_address_aliases (
    id UUID PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    raw_address TEXT NOT NULL,
    normalized_address TEXT NOT NULL,
    source TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS property_searches (
    id UUID PRIMARY KEY,
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    input_lat DOUBLE PRECISION NOT NULL,
    input_lon DOUBLE PRECISION NOT NULL,
    resolved_address TEXT,
    cache_status TEXT NOT NULL,
    errors JSONB NOT NULL DEFAULT '[]'::jsonb,
    langfuse_session_id TEXT,
    langfuse_trace_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS property_profiles (
    id UUID PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    search_id UUID REFERENCES property_searches(id) ON DELETE SET NULL,
    profile_version TEXT NOT NULL,
    status TEXT NOT NULL,
    summary TEXT,
    overall_confidence DOUBLE PRECISION,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    langfuse_trace_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_property_profiles_property_expires
    ON property_profiles(property_id, expires_at DESC);

CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    search_id UUID REFERENCES property_searches(id) ON DELETE SET NULL,
    source_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    source_uri TEXT,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    content_hash TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS imagery_assets (
    id UUID PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    source_id UUID REFERENCES data_sources(id) ON DELETE SET NULL,
    image_type TEXT NOT NULL,
    provider TEXT NOT NULL,
    url TEXT NOT NULL,
    storage_uri TEXT,
    content_hash TEXT,
    captured_at TIMESTAMPTZ,
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS segmentation_runs (
    id UUID PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    search_id UUID REFERENCES property_searches(id) ON DELETE SET NULL,
    image_asset_id UUID REFERENCES imagery_assets(id) ON DELETE SET NULL,
    model_name TEXT NOT NULL,
    model_version TEXT,
    checkpoint_ref TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw_response JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS segmentation_outputs (
    id UUID PRIMARY KEY,
    segmentation_run_id UUID NOT NULL REFERENCES segmentation_runs(id) ON DELETE CASCADE,
    target_type TEXT NOT NULL,
    prompt TEXT NOT NULL,
    mask_uri TEXT,
    overlay_uri TEXT,
    polygon_geojson JSONB,
    bbox JSONB,
    score DOUBLE PRECISION,
    raw_output JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS property_observations (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES property_profiles(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    field_key TEXT NOT NULL,
    value_json JSONB NOT NULL,
    value_text TEXT,
    confidence DOUBLE PRECISION,
    confidence_label TEXT,
    basis TEXT,
    evidence_kind TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_property_observations_profile_field
    ON property_observations(profile_id, field_key);

CREATE TABLE IF NOT EXISTS observation_sources (
    observation_id UUID NOT NULL REFERENCES property_observations(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    source_role TEXT NOT NULL,
    evidence_note TEXT,
    PRIMARY KEY (observation_id, source_id, source_role)
);

CREATE TABLE IF NOT EXISTS property_assumptions (
    id UUID PRIMARY KEY,
    profile_id UUID NOT NULL REFERENCES property_profiles(id) ON DELETE CASCADE,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    assumption_type TEXT NOT NULL,
    jurisdiction TEXT,
    statement TEXT NOT NULL,
    confidence DOUBLE PRECISION,
    basis TEXT,
    sources_used JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_extraction_runs (
    id UUID PRIMARY KEY,
    profile_id UUID REFERENCES property_profiles(id) ON DELETE SET NULL,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    search_id UUID REFERENCES property_searches(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_name TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    input_hash TEXT,
    raw_output_json JSONB NOT NULL,
    parsed_output_json JSONB,
    validation_errors JSONB,
    langfuse_trace_id TEXT,
    langfuse_observation_id TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS model_usage_events (
    id UUID PRIMARY KEY,
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    search_id UUID REFERENCES property_searches(id) ON DELETE SET NULL,
    provider TEXT NOT NULL,
    model_name TEXT NOT NULL,
    operation TEXT NOT NULL,
    langfuse_trace_id TEXT,
    langfuse_observation_id TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd NUMERIC,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS geospatial_snapshots (
    id UUID PRIMARY KEY,
    property_id UUID NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
    search_id UUID REFERENCES property_searches(id) ON DELETE SET NULL,
    source_id UUID REFERENCES data_sources(id) ON DELETE SET NULL,
    pois JSONB NOT NULL DEFAULT '[]'::jsonb,
    isochrone_geojson JSONB,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS ai_feedback (
    id UUID PRIMARY KEY,
    property_id UUID REFERENCES properties(id) ON DELETE SET NULL,
    profile_id UUID REFERENCES property_profiles(id) ON DELETE SET NULL,
    observation_id UUID REFERENCES property_observations(id) ON DELETE SET NULL,
    field_name TEXT NOT NULL,
    ai_value JSONB,
    ai_confidence DOUBLE PRECISION,
    corrected_value JSONB,
    notes TEXT,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO schema_migrations(version) VALUES ('0001_initial_property_intelligence')
ON CONFLICT (version) DO NOTHING;

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.config import settings
from app.models.schemas import ServiceResult

logger = logging.getLogger(__name__)
_postgres_schema_ready = False


def _using_postgres() -> bool:
    return bool(settings.DATABASE_URL)


def _get_conn():
    return psycopg.connect(settings.DATABASE_URL, row_factory=dict_row)


def _ensure_postgres_schema() -> None:
    global _postgres_schema_ready
    if _postgres_schema_ready:
        return

    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS properties (
                    id UUID PRIMARY KEY,
                    address TEXT NOT NULL,
                    lat DOUBLE PRECISION NOT NULL,
                    lon DOUBLE PRECISION NOT NULL,
                    neighborhood TEXT,
                    cross_streets TEXT,
                    created_at TIMESTAMPTZ NOT NULL,
                    updated_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS property_images (
                    id UUID PRIMARY KEY,
                    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
                    image_type TEXT NOT NULL,
                    url TEXT NOT NULL,
                    fetched_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ai_analysis (
                    id UUID PRIMARY KEY,
                    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
                    model_used TEXT NOT NULL,
                    property_type TEXT,
                    property_type_confidence DOUBLE PRECISION,
                    home_style TEXT,
                    home_style_confidence DOUBLE PRECISION,
                    stories TEXT,
                    stories_confidence DOUBLE PRECISION,
                    exterior_material TEXT,
                    exterior_material_confidence DOUBLE PRECISION,
                    has_pool BOOLEAN,
                    pool_confidence DOUBLE PRECISION,
                    tree_count_estimate INTEGER,
                    tree_count_confidence DOUBLE PRECISION,
                    has_garage BOOLEAN,
                    garage_confidence DOUBLE PRECISION,
                    parking_type TEXT,
                    parking_type_confidence DOUBLE PRECISION,
                    parking_spaces_estimate INTEGER,
                    parking_spaces_confidence DOUBLE PRECISION,
                    condition_estimate TEXT,
                    condition_confidence DOUBLE PRECISION,
                    approximate_age TEXT,
                    approximate_age_confidence DOUBLE PRECISION,
                    lot_shape TEXT,
                    lot_shape_confidence DOUBLE PRECISION,
                    has_fenced_yard BOOLEAN,
                    fence_confidence DOUBLE PRECISION,
                    has_solar_panels BOOLEAN,
                    solar_panels_confidence DOUBLE PRECISION,
                    roof_type TEXT,
                    roof_type_confidence DOUBLE PRECISION,
                    has_sidewalk BOOLEAN,
                    sidewalk_confidence DOUBLE PRECISION,
                    driveway_material TEXT,
                    driveway_material_confidence DOUBLE PRECISION,
                    has_chimney BOOLEAN,
                    chimney_confidence DOUBLE PRECISION,
                    has_deck_or_patio BOOLEAN,
                    deck_patio_confidence DOUBLE PRECISION,
                    has_gutters BOOLEAN,
                    gutters_confidence DOUBLE PRECISION,
                    has_detached_structure BOOLEAN,
                    detached_structure_confidence DOUBLE PRECISION,
                    has_ac_unit BOOLEAN,
                    ac_unit_confidence DOUBLE PRECISION,
                    raw_response JSONB NOT NULL DEFAULT '{}'::jsonb,
                    analyzed_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS geospatial_data (
                    id UUID PRIMARY KEY,
                    property_id UUID REFERENCES properties(id) ON DELETE CASCADE,
                    isochrone_geojson JSONB NOT NULL DEFAULT '{}'::jsonb,
                    pois JSONB NOT NULL DEFAULT '[]'::jsonb,
                    fetched_at TIMESTAMPTZ NOT NULL
                );

                CREATE TABLE IF NOT EXISTS ai_feedback (
                    id UUID PRIMARY KEY,
                    analysis_id TEXT,
                    property_id TEXT,
                    field_name TEXT NOT NULL,
                    ai_value JSONB,
                    ai_confidence DOUBLE PRECISION,
                    corrected_value JSONB NOT NULL,
                    notes TEXT,
                    submitted_at TIMESTAMPTZ NOT NULL
                );
                """
            )
    _postgres_schema_ready = True


def _get_client():
    """Create and return a Supabase client."""
    from supabase import create_client

    url = settings.SUPABASE_URL
    # Accept bare project ref or full URL
    if url and not url.startswith("http"):
        url = f"https://{url}.supabase.co"

    return create_client(url, settings.SUPABASE_SECRET_KEY)


async def save_property(
    address: str, lat: float, lon: float
) -> ServiceResult:
    """Insert a new property record into Supabase."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": str(uuid4()),
            "address": address,
            "lat": lat,
            "lon": lon,
            "created_at": now,
            "updated_at": now,
        }
        if _using_postgres():
            _ensure_postgres_schema()
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO properties (id, address, lat, lon, created_at, updated_at)
                        VALUES (%(id)s, %(address)s, %(lat)s, %(lon)s, %(created_at)s, %(updated_at)s)
                        RETURNING *
                        """,
                        record,
                    )
                    return ServiceResult(data=cur.fetchone(), error=None, source="postgres")

        client = _get_client()
        result = client.table("properties").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving property to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")


async def get_property(property_id: str) -> ServiceResult:
    """Fetch a property by ID from Supabase."""
    try:
        if _using_postgres():
            _ensure_postgres_schema()
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM properties WHERE id = %s", (property_id,))
                    row = cur.fetchone()
                    if not row:
                        return ServiceResult(
                            data=None, error="Property not found", source="postgres"
                        )
                    return ServiceResult(data=row, error=None, source="postgres")

        client = _get_client()
        result = (
            client.table("properties")
            .select("*")
            .eq("id", property_id)
            .execute()
        )
        if not result.data:
            return ServiceResult(
                data=None, error="Property not found", source="supabase"
            )
        return ServiceResult(data=result.data[0], error=None, source="supabase")
    except Exception as exc:
        logger.exception("Error fetching property from Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")


async def save_images(
    property_id: str, images: list[dict[str, Any]]
) -> ServiceResult:
    """Save property image records to Supabase."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        records = []
        for img in images:
            records.append(
                {
                    "id": str(uuid4()),
                    "property_id": property_id,
                    "image_type": img["image_type"],
                    "url": img["url"],
                    "fetched_at": now,
                }
            )
        if _using_postgres():
            _ensure_postgres_schema()
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    returned = []
                    for record in records:
                        cur.execute(
                            """
                            INSERT INTO property_images (id, property_id, image_type, url, fetched_at)
                            VALUES (%(id)s, %(property_id)s, %(image_type)s, %(url)s, %(fetched_at)s)
                            RETURNING *
                            """,
                            record,
                        )
                        returned.append(cur.fetchone())
                    return ServiceResult(data=returned, error=None, source="postgres")

        client = _get_client()
        result = client.table("property_images").insert(records).execute()
        return ServiceResult(
            data=result.data if result.data else records,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving images to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")


async def save_analysis(
    property_id: str, analysis: dict[str, Any]
) -> ServiceResult:
    """Save AI analysis results to Supabase."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": str(uuid4()),
            "property_id": property_id,
            "model_used": "gpt-4o",
            "property_type": analysis.get("property_type"),
            "property_type_confidence": analysis.get("property_type_confidence"),
            "home_style": analysis.get("home_style"),
            "home_style_confidence": analysis.get("home_style_confidence"),
            "stories": analysis.get("stories"),
            "stories_confidence": analysis.get("stories_confidence"),
            "exterior_material": analysis.get("exterior_material"),
            "exterior_material_confidence": analysis.get("exterior_material_confidence"),
            "has_pool": analysis.get("has_pool"),
            "pool_confidence": analysis.get("pool_confidence"),
            "tree_count_estimate": analysis.get("tree_count_estimate"),
            "tree_count_confidence": analysis.get("tree_count_confidence"),
            "has_garage": analysis.get("has_garage"),
            "garage_confidence": analysis.get("garage_confidence"),
            "parking_type": analysis.get("parking_type"),
            "parking_type_confidence": analysis.get("parking_type_confidence"),
            "parking_spaces_estimate": analysis.get("parking_spaces_estimate"),
            "parking_spaces_confidence": analysis.get("parking_spaces_confidence"),
            "condition_estimate": analysis.get("condition_estimate"),
            "condition_confidence": analysis.get("condition_confidence"),
            "approximate_age": analysis.get("approximate_age"),
            "approximate_age_confidence": analysis.get("approximate_age_confidence"),
            "lot_shape": analysis.get("lot_shape"),
            "lot_shape_confidence": analysis.get("lot_shape_confidence"),
            "has_fenced_yard": analysis.get("has_fenced_yard"),
            "fence_confidence": analysis.get("fence_confidence"),
            "has_solar_panels": analysis.get("has_solar_panels"),
            "solar_panels_confidence": analysis.get("solar_panels_confidence"),
            "roof_type": analysis.get("roof_type"),
            "roof_type_confidence": analysis.get("roof_type_confidence"),
            "has_sidewalk": analysis.get("has_sidewalk"),
            "sidewalk_confidence": analysis.get("sidewalk_confidence"),
            "driveway_material": analysis.get("driveway_material"),
            "driveway_material_confidence": analysis.get("driveway_material_confidence"),
            "has_chimney": analysis.get("has_chimney"),
            "chimney_confidence": analysis.get("chimney_confidence"),
            "has_deck_or_patio": analysis.get("has_deck_or_patio"),
            "deck_patio_confidence": analysis.get("deck_patio_confidence"),
            "has_gutters": analysis.get("has_gutters"),
            "gutters_confidence": analysis.get("gutters_confidence"),
            "has_detached_structure": analysis.get("has_detached_structure"),
            "detached_structure_confidence": analysis.get("detached_structure_confidence"),
            "has_ac_unit": analysis.get("has_ac_unit"),
            "ac_unit_confidence": analysis.get("ac_unit_confidence"),
            "raw_response": analysis,
            "analyzed_at": now,
        }
        if _using_postgres():
            _ensure_postgres_schema()
            postgres_record = {**record, "raw_response": Jsonb(record["raw_response"])}
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO ai_analysis (
                            id, property_id, model_used, property_type, property_type_confidence,
                            home_style, home_style_confidence, stories, stories_confidence,
                            exterior_material, exterior_material_confidence, has_pool, pool_confidence,
                            tree_count_estimate, tree_count_confidence, has_garage, garage_confidence,
                            parking_type, parking_type_confidence, parking_spaces_estimate,
                            parking_spaces_confidence, condition_estimate, condition_confidence,
                            approximate_age, approximate_age_confidence, lot_shape, lot_shape_confidence,
                            has_fenced_yard, fence_confidence, has_solar_panels, solar_panels_confidence,
                            roof_type, roof_type_confidence, has_sidewalk, sidewalk_confidence,
                            driveway_material, driveway_material_confidence, has_chimney, chimney_confidence,
                            has_deck_or_patio, deck_patio_confidence, has_gutters, gutters_confidence,
                            has_detached_structure, detached_structure_confidence, has_ac_unit,
                            ac_unit_confidence, raw_response, analyzed_at
                        ) VALUES (
                            %(id)s, %(property_id)s, %(model_used)s, %(property_type)s, %(property_type_confidence)s,
                            %(home_style)s, %(home_style_confidence)s, %(stories)s, %(stories_confidence)s,
                            %(exterior_material)s, %(exterior_material_confidence)s, %(has_pool)s, %(pool_confidence)s,
                            %(tree_count_estimate)s, %(tree_count_confidence)s, %(has_garage)s, %(garage_confidence)s,
                            %(parking_type)s, %(parking_type_confidence)s, %(parking_spaces_estimate)s,
                            %(parking_spaces_confidence)s, %(condition_estimate)s, %(condition_confidence)s,
                            %(approximate_age)s, %(approximate_age_confidence)s, %(lot_shape)s, %(lot_shape_confidence)s,
                            %(has_fenced_yard)s, %(fence_confidence)s, %(has_solar_panels)s, %(solar_panels_confidence)s,
                            %(roof_type)s, %(roof_type_confidence)s, %(has_sidewalk)s, %(sidewalk_confidence)s,
                            %(driveway_material)s, %(driveway_material_confidence)s, %(has_chimney)s, %(chimney_confidence)s,
                            %(has_deck_or_patio)s, %(deck_patio_confidence)s, %(has_gutters)s, %(gutters_confidence)s,
                            %(has_detached_structure)s, %(detached_structure_confidence)s, %(has_ac_unit)s,
                            %(ac_unit_confidence)s, %(raw_response)s::jsonb, %(analyzed_at)s
                        )
                        RETURNING *
                        """,
                        postgres_record,
                    )
                    return ServiceResult(data=cur.fetchone(), error=None, source="postgres")

        client = _get_client()
        result = client.table("ai_analysis").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving analysis to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")


async def save_geospatial(
    property_id: str, geo_data: dict[str, Any]
) -> ServiceResult:
    """Save geospatial data (isochrones, POIs) to Supabase."""
    try:
        now = datetime.now(timezone.utc).isoformat()
        record = {
            "id": str(uuid4()),
            "property_id": property_id,
            "isochrone_geojson": geo_data.get("isochrone_geojson", {}),
            "pois": geo_data.get("pois", []),
            "fetched_at": now,
        }
        if _using_postgres():
            _ensure_postgres_schema()
            postgres_record = {
                **record,
                "isochrone_geojson": Jsonb(record["isochrone_geojson"]),
                "pois": Jsonb(record["pois"]),
            }
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO geospatial_data (id, property_id, isochrone_geojson, pois, fetched_at)
                        VALUES (%(id)s, %(property_id)s, %(isochrone_geojson)s::jsonb, %(pois)s::jsonb, %(fetched_at)s)
                        RETURNING *
                        """,
                        postgres_record,
                    )
                    return ServiceResult(data=cur.fetchone(), error=None, source="postgres")

        client = _get_client()
        result = client.table("geospatial_data").insert(record).execute()
        return ServiceResult(
            data=result.data[0] if result.data else record,
            error=None,
            source="supabase",
        )
    except Exception as exc:
        logger.exception("Error saving geospatial data to Supabase")
        return ServiceResult(data=None, error=str(exc), source="supabase")

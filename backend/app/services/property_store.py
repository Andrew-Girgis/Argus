import hashlib
import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from app.config import settings
from app.db.pool import get_pool
from app.models.schemas import FeedbackRequest, ServiceResult

logger = logging.getLogger(__name__)

OBSERVATION_FIELDS: dict[str, str] = {
    "property_type": "structure",
    "home_style": "structure",
    "stories": "structure",
    "exterior_material": "structure",
    "has_pool": "lot_site",
    "tree_count_estimate": "lot_site",
    "has_garage": "parking",
    "parking_type": "parking",
    "parking_spaces_estimate": "parking",
    "condition_estimate": "condition",
    "approximate_age": "structure",
    "lot_shape": "lot_site",
    "has_fenced_yard": "lot_site",
    "has_solar_panels": "structure",
    "roof_type": "structure",
    "has_sidewalk": "neighborhood",
    "driveway_material": "parking",
    "has_chimney": "structure",
    "has_deck_or_patio": "lot_site",
    "has_gutters": "structure",
    "has_detached_structure": "lot_site",
    "has_ac_unit": "mechanicals",
}

CONFIDENCE_FIELDS = {
    "property_type": "property_type_confidence",
    "home_style": "home_style_confidence",
    "stories": "stories_confidence",
    "exterior_material": "exterior_material_confidence",
    "has_pool": "pool_confidence",
    "tree_count_estimate": "tree_count_confidence",
    "has_garage": "garage_confidence",
    "parking_type": "parking_type_confidence",
    "parking_spaces_estimate": "parking_spaces_confidence",
    "condition_estimate": "condition_confidence",
    "approximate_age": "approximate_age_confidence",
    "lot_shape": "lot_shape_confidence",
    "has_fenced_yard": "fence_confidence",
    "has_solar_panels": "solar_panels_confidence",
    "roof_type": "roof_type_confidence",
    "has_sidewalk": "sidewalk_confidence",
    "driveway_material": "driveway_material_confidence",
    "has_chimney": "chimney_confidence",
    "has_deck_or_patio": "deck_patio_confidence",
    "has_gutters": "gutters_confidence",
    "has_detached_structure": "detached_structure_confidence",
    "has_ac_unit": "ac_unit_confidence",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_address(address: str) -> str:
    """Return a stable cache key representation for address-first lookup."""
    normalized = address.lower().strip()
    normalized = re.sub(r"[.,#]", " ", normalized)
    normalized = re.sub(r"\b(street)\b", "st", normalized)
    normalized = re.sub(r"\b(avenue)\b", "ave", normalized)
    normalized = re.sub(r"\b(road)\b", "rd", normalized)
    normalized = re.sub(r"\b(drive)\b", "dr", normalized)
    normalized = re.sub(r"\b(ontario)\b", "on", normalized)
    normalized = re.sub(r"\b(canada)\b", "ca", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def address_hash(address: str) -> str:
    return hashlib.sha256(normalize_address(address).encode("utf-8")).hexdigest()


def _json(value: Any) -> str:
    return json.dumps(value, default=str)


def _from_json(value: Any) -> Any:
    if value is None or isinstance(value, dict | list):
        return value
    return json.loads(value)


def _record_to_property(record: Any) -> dict[str, Any]:
    return {
        "id": str(record["id"]),
        "address": record["display_address"],
        "lat": record["latitude"],
        "lon": record["longitude"],
        "neighborhood": record["neighborhood"],
        "cross_streets": record["cross_streets"],
        "created_at": record["created_at"].isoformat(),
        "updated_at": record["updated_at"].isoformat(),
    }


async def get_cached_profile(address: str) -> ServiceResult:
    """Return a fresh cached compatibility response for an address, if available."""
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            prop = await conn.fetchrow(
                "SELECT * FROM properties WHERE address_hash = $1",
                address_hash(address),
            )
            if not prop:
                return ServiceResult(data=None, error=None, source="postgres")

            profile = await conn.fetchrow(
                """
                SELECT * FROM property_profiles
                WHERE property_id = $1 AND expires_at > NOW() AND status = 'complete'
                ORDER BY generated_at DESC
                LIMIT 1
                """,
                prop["id"],
            )
            if not profile:
                return ServiceResult(data=None, error=None, source="postgres")

            images = await conn.fetch(
                """
                SELECT id, property_id, image_type, url, retrieved_at
                FROM imagery_assets
                WHERE property_id = $1
                ORDER BY retrieved_at DESC
                LIMIT 10
                """,
                prop["id"],
            )
            extraction = await conn.fetchrow(
                """
                SELECT parsed_output_json
                FROM ai_extraction_runs
                WHERE profile_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                profile["id"],
            )
            geo = await conn.fetchrow(
                """
                SELECT id, property_id, pois, fetched_at
                FROM geospatial_snapshots
                WHERE property_id = $1
                ORDER BY fetched_at DESC
                LIMIT 1
                """,
                prop["id"],
            )
            seg = await conn.fetchrow(
                """
                SELECT raw_response
                FROM segmentation_runs
                WHERE property_id = $1
                ORDER BY created_at DESC
                LIMIT 1
                """,
                prop["id"],
            )

        analysis = _from_json(extraction["parsed_output_json"]) if extraction else None
        data = {
            "property": _record_to_property(prop),
            "images": [
                {
                    "id": str(row["id"]),
                    "property_id": str(row["property_id"]),
                    "image_type": row["image_type"],
                    "url": row["url"],
                    "fetched_at": row["retrieved_at"].isoformat(),
                }
                for row in images
            ],
            "analysis": analysis,
            "segmentation": _from_json(seg["raw_response"]) if seg else None,
            "geospatial": (
                {
                    "id": str(geo["id"]),
                    "property_id": str(geo["property_id"]),
                    "pois": _from_json(geo["pois"]),
                    "fetched_at": geo["fetched_at"].isoformat(),
                }
                if geo
                else None
            ),
            "errors": [],
            "cache": {"status": "hit", "profile_id": str(profile["id"])},
        }
        return ServiceResult(data=data, error=None, source="postgres")
    except Exception as exc:
        logger.exception("Error reading cached property profile")
        return ServiceResult(data=None, error=str(exc), source="postgres")


async def create_search(
    lat: float,
    lon: float,
    address: str | None,
    cache_status: str,
    property_id: str | None = None,
    errors: list[str] | None = None,
) -> ServiceResult:
    try:
        pool = await get_pool()
        search_id = uuid4()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO property_searches(
                    id, property_id, input_lat, input_lon, resolved_address,
                    cache_status, errors
                ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                """,
                search_id,
                UUID(property_id) if property_id else None,
                lat,
                lon,
                address,
                cache_status,
                _json(errors or []),
            )
        return ServiceResult(data={"id": str(search_id)}, error=None, source="postgres")
    except Exception as exc:
        logger.exception("Error creating property search")
        return ServiceResult(data=None, error=str(exc), source="postgres")


async def save_profile(
    *,
    address: str,
    lat: float,
    lon: float,
    neighborhood: str | None,
    cross_streets: str | None,
    city: str | None,
    search_id: str | None,
    images: list[dict[str, Any]],
    analysis: dict[str, Any] | None,
    segmentation: dict[str, Any] | None,
    pois: list[dict[str, Any]],
    errors: list[str],
) -> ServiceResult:
    """Persist a complete property profile and return compatibility objects."""
    try:
        pool = await get_pool()
        now = _now()
        expires_at = now + timedelta(days=settings.PROPERTY_CACHE_TTL_DAYS)
        prop_id = uuid4()
        profile_id = uuid4()
        addr_hash = address_hash(address)
        norm_address = normalize_address(address)
        async with pool.acquire() as conn:
            async with conn.transaction():
                prop = await conn.fetchrow(
                    "SELECT * FROM properties WHERE address_hash = $1",
                    addr_hash,
                )
                if prop:
                    prop_id = prop["id"]
                    prop = await conn.fetchrow(
                        """
                        UPDATE properties
                        SET display_address = $2, latitude = $3, longitude = $4,
                            neighborhood = $5, cross_streets = $6, city = $7,
                            updated_at = $8
                        WHERE id = $1
                        RETURNING *
                        """,
                        prop_id,
                        address,
                        lat,
                        lon,
                        neighborhood,
                        cross_streets,
                        city,
                        now,
                    )
                else:
                    prop = await conn.fetchrow(
                        """
                        INSERT INTO properties(
                            id, canonical_address, address_hash, normalized_components,
                            display_address, country, province_state, municipality,
                            city, neighborhood, cross_streets, latitude, longitude,
                            created_at, updated_at
                        ) VALUES ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $14)
                        RETURNING *
                        """,
                        prop_id,
                        norm_address,
                        addr_hash,
                        _json({"normalized_address": norm_address}),
                        address,
                        "Canada" if "canada" in address.lower() else None,
                        "ON" if re.search(r"\b(on|ontario)\b", address, re.I) else None,
                        city,
                        city,
                        neighborhood,
                        cross_streets,
                        lat,
                        lon,
                        now,
                    )

                await conn.execute(
                    """
                    INSERT INTO property_address_aliases(id, property_id, raw_address, normalized_address, source)
                    VALUES ($1, $2, $3, $4, $5)
                    """,
                    uuid4(),
                    prop_id,
                    address,
                    norm_address,
                    "google_geocode",
                )

                if search_id:
                    await conn.execute(
                        "UPDATE property_searches SET property_id = $1 WHERE id = $2",
                        prop_id,
                        UUID(search_id),
                    )

                await conn.execute(
                    """
                    INSERT INTO property_profiles(
                        id, property_id, search_id, profile_version, status,
                        generated_at, expires_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    profile_id,
                    prop_id,
                    UUID(search_id) if search_id else None,
                    "v1",
                    "complete",
                    now,
                    expires_at,
                )

                image_rows = []
                for image in images:
                    source_id = uuid4()
                    image_id = uuid4()
                    await conn.execute(
                        """
                        INSERT INTO data_sources(
                            id, property_id, search_id, source_type, provider,
                            source_uri, retrieved_at, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                        """,
                        source_id,
                        prop_id,
                        UUID(search_id) if search_id else None,
                        image["image_type"],
                        "google_maps",
                        image["url"],
                        now,
                        _json({}),
                    )
                    await conn.execute(
                        """
                        INSERT INTO imagery_assets(
                            id, property_id, source_id, image_type, provider, url, retrieved_at, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb)
                        """,
                        image_id,
                        prop_id,
                        source_id,
                        image["image_type"],
                        "google_maps",
                        image["url"],
                        now,
                        _json({}),
                    )
                    image_rows.append({
                        "id": str(image_id),
                        "property_id": str(prop_id),
                        "image_type": image["image_type"],
                        "url": image["url"],
                        "fetched_at": now.isoformat(),
                    })

                if analysis:
                    analysis_id = str(uuid4())
                    analysis_with_meta = {
                        "id": analysis_id,
                        "property_id": str(prop_id),
                        "model_used": settings.OPENAI_SEGMENTED_REASONING_MODEL or settings.OPENAI_VISION_MODEL,
                        **analysis,
                        "raw_response": analysis,
                        "analyzed_at": now.isoformat(),
                    }
                    await conn.execute(
                        """
                        INSERT INTO ai_extraction_runs(
                            id, profile_id, property_id, search_id, provider, model,
                            prompt_name, prompt_version, raw_output_json, parsed_output_json
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10::jsonb)
                        """,
                        uuid4(),
                        profile_id,
                        prop_id,
                        UUID(search_id) if search_id else None,
                        "openai",
                        settings.OPENAI_SEGMENTED_REASONING_MODEL or settings.OPENAI_VISION_MODEL,
                        "property.segmented_reasoning",
                        "v1",
                        _json(analysis),
                        _json(analysis_with_meta),
                    )
                    await _insert_observations(conn, profile_id, prop_id, analysis)
                else:
                    analysis_with_meta = None

                if segmentation:
                    await conn.execute(
                        """
                        INSERT INTO segmentation_runs(
                            id, property_id, search_id, model_name, checkpoint_ref,
                            status, metadata, raw_response
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb)
                        """,
                        uuid4(),
                        prop_id,
                        UUID(search_id) if search_id else None,
                        settings.SAM_MODEL_ID,
                        settings.SAM_MODEL_ID,
                        segmentation.get("status", "complete"),
                        _json({}),
                        _json(segmentation),
                    )

                geo_id = uuid4()
                await conn.execute(
                    """
                    INSERT INTO geospatial_snapshots(
                        id, property_id, search_id, pois, metadata, fetched_at, expires_at
                    ) VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6, $7)
                    """,
                    geo_id,
                    prop_id,
                    UUID(search_id) if search_id else None,
                    _json(pois),
                    _json({}),
                    now,
                    expires_at,
                )

        response = {
            "property": _record_to_property(prop),
            "images": image_rows,
            "analysis": analysis_with_meta,
            "segmentation": segmentation,
            "geospatial": {
                "id": str(geo_id),
                "property_id": str(prop_id),
                "pois": pois,
                "fetched_at": now.isoformat(),
            },
            "errors": errors,
            "cache": {"status": "miss", "profile_id": str(profile_id)},
        }
        return ServiceResult(data=response, error=None, source="postgres")
    except Exception as exc:
        logger.exception("Error saving property profile")
        return ServiceResult(data=None, error=str(exc), source="postgres")


async def _insert_observations(conn: Any, profile_id: UUID, prop_id: UUID, analysis: dict[str, Any]) -> None:
    for field_key, category in OBSERVATION_FIELDS.items():
        if field_key not in analysis:
            continue
        confidence = analysis.get(CONFIDENCE_FIELDS.get(field_key, ""))
        basis = None
        raw_field = analysis.get(field_key)
        if isinstance(raw_field, dict):
            basis = raw_field.get("basis")
            value = raw_field.get("value")
            confidence = raw_field.get("confidence", confidence)
            evidence_kind = raw_field.get("evidence_kind", "inferred")
        else:
            value = raw_field
            evidence_kind = "observed" if confidence and confidence >= 0.8 else "inferred"
        await conn.execute(
            """
            INSERT INTO property_observations(
                id, profile_id, property_id, category, field_key, value_json,
                value_text, confidence, confidence_label, basis, evidence_kind
            ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10, $11)
            """,
            uuid4(),
            profile_id,
            prop_id,
            category,
            field_key,
            _json(value),
            None if value is None else str(value),
            confidence,
            _confidence_label(confidence),
            basis,
            evidence_kind,
        )

    enhanced = analysis.get("enhanced_intelligence")
    if isinstance(enhanced, dict):
        for field_key, wrapped in enhanced.items():
            if not isinstance(wrapped, dict):
                continue
            value = wrapped.get("value")
            confidence = wrapped.get("confidence")
            await conn.execute(
                """
                INSERT INTO property_observations(
                    id, profile_id, property_id, category, field_key, value_json,
                    value_text, confidence, confidence_label, basis, evidence_kind
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10, $11)
                """,
                uuid4(),
                profile_id,
                prop_id,
                "enhanced_intelligence",
                field_key,
                _json(value),
                None if value is None else str(value),
                confidence,
                _confidence_label(confidence),
                wrapped.get("basis"),
                wrapped.get("evidence_kind", "inferred"),
            )


def _confidence_label(confidence: Any) -> str | None:
    if not isinstance(confidence, int | float):
        return None
    if confidence >= 0.75:
        return "high"
    if confidence >= 0.45:
        return "medium"
    return "low"


async def save_feedback(req: FeedbackRequest) -> ServiceResult:
    try:
        pool = await get_pool()
        record = {
            "id": str(uuid4()),
            "analysis_id": req.analysis_id,
            "property_id": req.property_id,
            "profile_id": req.profile_id,
            "observation_id": req.observation_id,
            "field_name": req.field_name,
            "ai_value": req.ai_value,
            "ai_confidence": req.ai_confidence,
            "corrected_value": req.corrected_value,
            "notes": req.notes,
            "submitted_at": _now().isoformat(),
        }
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ai_feedback(
                    id, property_id, profile_id, observation_id, field_name, ai_value, ai_confidence,
                    corrected_value, notes, submitted_at
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8::jsonb, $9, $10)
                """,
                UUID(record["id"]),
                UUID(req.property_id) if req.property_id else None,
                UUID(req.profile_id) if req.profile_id else None,
                UUID(req.observation_id) if req.observation_id else None,
                req.field_name,
                _json(req.ai_value),
                req.ai_confidence,
                _json(req.corrected_value),
                req.notes,
                _now(),
            )
        return ServiceResult(data=record, error=None, source="postgres")
    except Exception as exc:
        logger.exception("Error saving feedback")
        return ServiceResult(data=None, error=str(exc), source="postgres")

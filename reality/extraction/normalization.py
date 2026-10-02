import json
from typing import Any, Dict, List
from pydantic import ValidationError

from reality.extraction.contracts import (
    NormalizedClaim,
    DroppedClaim,
    NormalizationMalformed,
    NormalizationSuccess,
    NormalizationResult
)


def normalize(raw_output: Any) -> NormalizationResult:
    """
    Structurally maps provider output to NormalizedClaims.
    Does NOT perform semantic validation, data inference, or claim repair.
    """
    # 1. Structural Discovery: Must be a direct list of fragments.
    if not isinstance(raw_output, list):
        return NormalizationMalformed(
            reason="Provider output payload must be a direct list of fragments."
        )

    claims: List[NormalizedClaim] = []
    dropped: List[DroppedClaim] = []

    # 2. Structural Mapping: Process individual fragments
    for fragment in raw_output:
        if not isinstance(fragment, dict):
            dropped.append(
                DroppedClaim(
                    stage="normalization",
                    reason="Fragment is not a dictionary.",
                    payload_projection=_safe_json_projection(fragment)
                )
            )
            continue

        try:
            # Strict structural mapping. 
            # Missing or semantically empty fields pass through (Class 5 domain).
            # Extra fields or invalid types will raise ValidationError (Class 4 domain).
            claim = NormalizedClaim.model_validate(fragment)
            claims.append(claim)
            
        except ValidationError as e:
            dropped.append(
                DroppedClaim(
                    stage="normalization",
                    reason=f"Structural mapping failed: {_format_error_paths(e)}",
                    payload_projection=_safe_json_projection(fragment)
                )
            )

    return NormalizationSuccess(claims=claims, dropped=dropped)


def _format_error_paths(error: ValidationError) -> str:
    """
    Builds a deterministic, provider-agnostic description of which field
    paths caused a ValidationError.

    Each Pydantic error location (a tuple such as ("type_hints", "A")) is
    rendered as a dotted path ("type_hints.A"). Paths are de-duplicated and
    sorted so the resulting reason string is stable regardless of the
    order in which Pydantic reports errors. Error messages and input values
    are intentionally excluded to avoid leaking provider content into the
    audit reason.
    """
    paths = {
        ".".join(str(part) for part in err["loc"]) or "<root>"
        for err in error.errors()
    }
    return ", ".join(sorted(paths))

def _safe_json_projection(data: Any) -> Dict[str, Any]:
    """
    Ensures the dropped payload is a deterministic, JSON-compatible dictionary projection.
    Uses a stable "value" key for non-dictionary fragments.
    """
    if isinstance(data, dict):
        try:
            serialized = json.dumps(data)
            return json.loads(serialized)
        except (TypeError, ValueError):
            return {"error": "unserializable_dict"}
    else:
        try:
            # Use stable key "value" for primitives
            serialized = json.dumps({"value": data})
            return json.loads(serialized)
        except (TypeError, ValueError):
            return {"error": "unserializable_value"}
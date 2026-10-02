import copy
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, get_args

import pytest
from pydantic import ValidationError

from reality.classification.contracts import (
    MAX_DETAIL_TEXT_CHARS,
    MAX_ERROR_DETAILS,
    MAX_PAYLOAD_PREVIEW_CHARS,
    REASON_CODE_TO_ERROR_TYPE,
    ClassificationReasonCode,
    DroppedProposal,
    ErrorDetail,
)
from reality.classification.normalization import normalize_classification
from reality.classification.schemas import CandidateAttribute, TemporalMarker

OBS_ID = "obs_123"
FIXED = datetime(2026, 1, 1, tzinfo=timezone.utc)
ZERO_HASH = "0" * 64


def clock() -> datetime:
    return FIXED


def run(raw: object, observation_id: str = OBS_ID):
    return normalize_classification(raw, observation_id, clock=clock)


def run_one(payload: object, observation_id: str = OBS_ID):
    """The provider contract: a root is always a list of candidates."""
    return run([payload], observation_id)


@pytest.fixture
def valid_payload() -> dict[str, Any]:
    return {
        "source_observation_id": OBS_ID,
        "semantic_type": "Fact",
        "predicate": "knows",
        "classification_confidence": 0.8,
        "derivation_metadata": {"derivation_type": "explicit", "engine": "test_engine"},
    }


class TestAcceptance:
    def test_valid_payload_with_nested_objects_is_accepted(self, valid_payload):
        result = run_one(valid_payload)

        assert len(result.accepted) == 1
        assert len(result.dropped) == 0
        assert result.accepted[0].derivation_metadata.engine == "test_engine"

    def test_nested_arrays_become_immutable_tuples(self, valid_payload):
        valid_payload["candidate_subject_descriptor"] = {
            "label": "Sara",
            "attributes": [{"key": "role", "value": "coworker"}],
        }

        result = run_one(valid_payload)

        descriptor = result.accepted[0].candidate_subject_descriptor
        assert descriptor is not None
        assert descriptor.attributes == (CandidateAttribute(key="role", value="coworker"),)

    def test_temporal_markers_are_accepted_as_typed_tuple(self, valid_payload):
        valid_payload["temporal_markers"] = [{"label": "at", "value": "2026-01-01"}]

        result = run_one(valid_payload)

        assert result.accepted[0].temporal_markers == (
            TemporalMarker(label="at", value="2026-01-01"),
        )

    @pytest.mark.parametrize("edge", [0.0, 1.0])
    def test_confidence_bounds_inclusive(self, valid_payload, edge):
        valid_payload["classification_confidence"] = edge
        assert len(run_one(valid_payload).accepted) == 1

    def test_input_is_never_mutated(self, valid_payload):
        before = copy.deepcopy(valid_payload)
        run([valid_payload])
        assert valid_payload == before


class TestRejectionOnly:
    @pytest.mark.parametrize("bad", ["0.8", 1, 0, True, 1.5])
    def test_bad_confidence_is_rejected_not_coerced(self, valid_payload, bad):
        valid_payload["classification_confidence"] = bad

        result = run_one(valid_payload)

        assert len(result.accepted) == 0
        assert len(result.dropped) == 1
        drop = result.dropped[0]
        assert drop.error_type == "FirewallRejection"
        assert drop.reason_code == "SCHEMA_VIOLATION"
        assert drop.details[0].loc == ("classification_confidence",)

    def test_root_authority_leak_is_dropped_with_machine_readable_detail(self, valid_payload):
        valid_payload["entity_uuid"] = "uuid-123"

        drop = run_one(valid_payload).dropped[0]

        assert drop.reason_code == "SCHEMA_VIOLATION"
        assert drop.details[0].type == "extra_forbidden"
        assert drop.details[0].loc == ("entity_uuid",)

    def test_nested_authority_leak_is_dropped(self, valid_payload):
        valid_payload["candidate_subject_descriptor"] = {
            "label": "Sara",
            "entity_uuid": "uuid-999",
        }

        result = run([valid_payload])

        assert len(result.accepted) == 0
        detail = result.dropped[0].details[0]
        assert detail.type == "extra_forbidden"
        assert detail.loc[-1] == "entity_uuid"

    def test_identity_smuggled_through_label_is_dropped(self, valid_payload):
        valid_payload["candidate_subject_descriptor"] = {"label": "Sara:person_123"}

        result = run_one(valid_payload)

        assert len(result.accepted) == 0
        assert result.dropped[0].reason_code == "SCHEMA_VIOLATION"
        assert result.dropped[0].details[0].loc[-1] == "label"

    def test_old_free_form_temporal_markers_are_rejected(self, valid_payload):
        valid_payload["temporal_markers"] = {"when": "before yesterday maybe"}

        result = run_one(valid_payload)

        assert len(result.accepted) == 0
        assert result.dropped[0].reason_code == "SCHEMA_VIOLATION"

    def test_unknown_temporal_label_is_rejected(self, valid_payload):
        valid_payload["temporal_markers"] = [{"label": "sometime", "value": "x"}]

        assert len(run_one(valid_payload).accepted) == 0

    def test_audit_details_do_not_reembed_the_payload(self, valid_payload):
        valid_payload["entity_uuid"] = "SECRET-MARKER"

        drop = run_one(valid_payload).dropped[0]

        for detail in drop.details:
            assert "SECRET-MARKER" not in detail.msg
            assert not hasattr(detail, "input")
            assert not hasattr(detail, "ctx")


class TestContainers:
    def test_mixed_garbage_batch_resilience(self, valid_payload):
        result = run([valid_payload, "hello", 123, {}, [], None])

        assert len(result.accepted) == 1
        assert [d.reason_code for d in result.dropped] == [
            "NOT_A_DICTIONARY",
            "NOT_A_DICTIONARY",
            "SCHEMA_VIOLATION",
            "NOT_A_DICTIONARY",
            "NOT_A_DICTIONARY",
        ]
        assert [d.error_type for d in result.dropped] == [
            "InvalidPayloadType",
            "InvalidPayloadType",
            "FirewallRejection",
            "InvalidPayloadType",
            "InvalidPayloadType",
        ]

    def test_bare_dict_root_is_malformed_like_in_extraction(self, valid_payload):
        """Same contract as extraction.normalize: the root must be a list."""
        result = run(valid_payload)

        assert result.accepted == ()
        assert result.dropped[0].error_type == "MalformedContainer"
        assert result.dropped[0].reason_code == "INVALID_ROOT_TYPE"

    def test_tuple_root_is_malformed_like_in_extraction(self, valid_payload):
        result = run((valid_payload,))

        assert result.accepted == ()
        assert result.dropped[0].reason_code == "INVALID_ROOT_TYPE"

    def test_none_root(self):
        result = run(None)
        assert len(result.accepted) == 0
        assert result.dropped[0].error_type == "MalformedContainer"
        assert result.dropped[0].reason_code == "NULL_OUTPUT"

    def test_string_root(self):
        result = run("Internal Server Error from LLM")
        assert len(result.accepted) == 0
        assert result.dropped[0].error_type == "MalformedContainer"
        assert result.dropped[0].reason_code == "INVALID_ROOT_TYPE"


class TestJsonDomainGate:
    def test_non_string_key_is_dropped_not_crashed(self):
        result = run([{1: "x"}])

        assert len(result.accepted) == 0
        assert result.dropped[0].reason_code == "NOT_JSON_DOMAIN"

    def test_non_json_object_is_dropped_and_projected_without_str(self, valid_payload):
        valid_payload["predicate"] = Decimal("1.5")

        drop = run_one(valid_payload).dropped[0]

        assert drop.reason_code == "NOT_JSON_DOMAIN"
        preview = json.loads(drop.payload_preview)
        assert preview["predicate"] == {"unserializable_type": "Decimal"}

    @pytest.mark.parametrize("bad", [float("nan"), float("inf")])
    def test_non_finite_float_is_dropped(self, valid_payload, bad):
        valid_payload["classification_confidence"] = bad

        drop = run_one(valid_payload).dropped[0]

        assert drop.reason_code == "NOT_JSON_DOMAIN"
        preview = json.loads(drop.payload_preview)
        assert preview["classification_confidence"] == {"non_finite_float": True}

    def test_lone_surrogate_string_does_not_break_the_audit(self, valid_payload):
        valid_payload["predicate"] = "bad\ud800text"

        result = run_one(valid_payload)

        # Whether the JSON parser accepts or rejects the lone surrogate is not
        # the point; the audit path must simply never raise.
        assert len(result.accepted) + len(result.dropped) == 1

    def test_very_deep_nesting_does_not_raise(self, valid_payload):
        deep: list = []
        for _ in range(10_000):
            deep = [deep]
        valid_payload["temporal_markers"] = deep

        result = run_one(valid_payload)

        assert len(result.accepted) == 0
        assert result.dropped[0].reason_code == "NOT_JSON_DOMAIN"

    def test_cyclic_payload_does_not_raise(self, valid_payload):
        cyc: dict[str, Any] = {}
        cyc["self"] = cyc
        valid_payload["temporal_markers"] = cyc

        result = run_one(valid_payload)

        assert result.dropped[0].reason_code == "NOT_JSON_DOMAIN"


class TestBoundedAudit:
    def test_preview_is_bounded_and_flagged_when_truncated(self, valid_payload):
        valid_payload["predicate"] = "x" * 10_000

        drop = run_one(valid_payload).dropped[0]

        assert drop.reason_code == "SCHEMA_VIOLATION"
        assert len(drop.payload_preview) <= MAX_PAYLOAD_PREVIEW_CHARS
        assert drop.payload_truncated is True

    def test_short_payload_is_not_flagged_truncated(self):
        drop = run("junk").dropped[0]

        assert drop.payload_truncated is False
        assert json.loads(drop.payload_preview) == "junk"

    def test_raw_payload_is_not_retained(self, valid_payload):
        drop = run_one(valid_payload | {"entity_uuid": "x"}).dropped[0]

        assert not hasattr(drop, "raw_payload")

    def test_hash_is_deterministic_and_discriminating(self, valid_payload):
        a1 = run_one(valid_payload | {"entity_uuid": "a"}).dropped[0]
        a2 = run_one(valid_payload | {"entity_uuid": "a"}).dropped[0]
        b = run_one(valid_payload | {"entity_uuid": "b"}).dropped[0]

        assert a1.projection_hash == a2.projection_hash
        assert a1.projection_hash != b.projection_hash
        assert len(a1.projection_hash) == 64

    def test_hash_ignores_dict_key_order(self, valid_payload):
        reordered = dict(reversed(list(valid_payload.items())))
        reordered["entity_uuid"] = "a"
        original = valid_payload | {"entity_uuid": "a"}

        assert (
            run_one(reordered).dropped[0].projection_hash
            == run_one(original).dropped[0].projection_hash
        )


class TestProvenance:
    def test_mismatched_source_observation_id_is_rejected(self, valid_payload):
        valid_payload["source_observation_id"] = "obs_999"

        result = run_one(valid_payload, observation_id=OBS_ID)

        assert len(result.accepted) == 0
        drop = result.dropped[0]
        assert drop.reason_code == "PROVENANCE_MISMATCH"
        assert drop.error_type == "FirewallRejection"


class TestAuditContract:
    def test_results_are_reproducible_with_injected_clock(self, valid_payload):
        batch = [valid_payload, "junk", {"a": 1}]
        assert run(batch) == run(batch)
        assert all(d.created_at == FIXED for d in run(batch).dropped)

    def test_every_reason_code_has_exactly_one_error_type(self):
        assert set(get_args(ClassificationReasonCode)) == set(REASON_CODE_TO_ERROR_TYPE)

    def test_unknown_reason_code_rejected(self):
        with pytest.raises(ValidationError):
            DroppedProposal(
                payload_preview="{}",
                payload_truncated=False,
                projection_hash=ZERO_HASH,
                error_type="MalformedContainer",
                reason_code="NULL",  # type: ignore[arg-type]
                details=(),
                created_at=FIXED,
            )

    def test_error_type_must_match_reason_code(self):
        with pytest.raises(ValidationError):
            DroppedProposal(
                payload_preview="{}",
                payload_truncated=False,
                projection_hash=ZERO_HASH,
                error_type="MalformedContainer",
                reason_code="SCHEMA_VIOLATION",
                details=(),
                created_at=FIXED,
            )

    def test_hash_must_be_a_sha256_hex_digest(self):
        with pytest.raises(ValidationError):
            DroppedProposal(
                payload_preview="{}",
                payload_truncated=False,
                projection_hash="none",
                error_type="MalformedContainer",
                reason_code="NULL_OUTPUT",
                details=(),
                created_at=FIXED,
            )


class MyInt(int):
    pass


class MyFloat(float):
    pass


class MyStr(str):
    pass


class MyDict(dict):
    pass


class TestExactTypesOnly:
    @pytest.mark.parametrize(
        "value",
        [MyInt(1), MyFloat(0.5), MyStr("x"), MyDict(a=1)],
        ids=["int-subclass", "float-subclass", "str-subclass", "dict-subclass"],
    )
    def test_subclasses_of_json_types_do_not_pass_the_gate(self, valid_payload, value):
        valid_payload["unknown"] = value

        drop = run_one(valid_payload).dropped[0]

        assert drop.reason_code == "NOT_JSON_DOMAIN"

    def test_numpy_scalars_do_not_pass_the_gate(self, valid_payload):
        np = pytest.importorskip("numpy")
        for value in (np.int64(1), np.float32(0.5), np.float64(0.8), np.bool_(True)):
            payload = dict(valid_payload)
            payload["unknown"] = value

            assert run_one(payload).dropped[0].reason_code == "NOT_JSON_DOMAIN"

    def test_numpy_float64_cannot_sneak_in_as_confidence(self, valid_payload):
        np = pytest.importorskip("numpy")
        valid_payload["classification_confidence"] = np.float64(0.8)

        result = run_one(valid_payload)

        assert len(result.accepted) == 0
        assert result.dropped[0].reason_code == "NOT_JSON_DOMAIN"


class TestResourceSafety:
    def test_shared_reference_expansion_cannot_blow_up(self, valid_payload):
        """
        60 levels of [x, x] is tiny in memory but has 2**60 paths. Depth limits
        do not stop it; the node budget does. Without it this test never ends.
        """
        node: list = []
        for _ in range(60):
            node = [node, node]
        valid_payload["temporal_markers"] = node

        result = run_one(valid_payload)

        assert len(result.accepted) == 0
        assert result.dropped[0].reason_code == "NOT_JSON_DOMAIN"

    def test_huge_integer_is_dropped_instead_of_crashing_the_batch(self, valid_payload):
        """json.dumps raises ValueError on ints over Python's digit limit."""
        bad = dict(valid_payload)
        bad["predicate"] = 10**5000

        result = run([bad, valid_payload])

        assert len(result.accepted) == 1
        assert result.dropped[0].reason_code == "NOT_JSON_DOMAIN"
        preview = json.loads(result.dropped[0].payload_preview)
        assert preview["predicate"] == {"int_out_of_range": True}

    def test_huge_payload_keeps_the_audit_bounded(self, valid_payload):
        valid_payload["junk"] = {f"k{i}": i for i in range(100_000)}

        drop = run_one(valid_payload).dropped[0]

        assert len(drop.payload_preview) <= MAX_PAYLOAD_PREVIEW_CHARS
        assert len(drop.projection_hash) == 64
        # The projection kept 64 entries and recorded how many it dropped.
        assert '"<truncated_items>":99936' in drop.payload_preview

    def test_thousands_of_schema_errors_are_capped(self, valid_payload):
        bad_marker = {"label": "nope", "value": ""}
        valid_payload["temporal_markers"] = [bad_marker] * 20_000

        drop = run_one(valid_payload).dropped[0]

        assert drop.reason_code == "SCHEMA_VIOLATION"
        assert len(drop.details) == MAX_ERROR_DETAILS
        assert drop.details_omitted > 0

    def test_hostile_key_cannot_bloat_the_error_location(self, valid_payload):
        valid_payload["k" * 100_000] = 1

        drop = run_one(valid_payload).dropped[0]

        assert drop.details[0].type == "extra_forbidden"
        for part in drop.details[0].loc:
            if isinstance(part, str):
                assert len(part) <= MAX_DETAIL_TEXT_CHARS

    def test_error_detail_contract_rejects_oversized_text(self):
        with pytest.raises(ValidationError):
            ErrorDetail(type="x", loc=("k" * (MAX_DETAIL_TEXT_CHARS + 1),), msg="m")
        with pytest.raises(ValidationError):
            ErrorDetail(type="x", loc=("a",), msg="m" * (MAX_DETAIL_TEXT_CHARS + 1))

    def test_details_omitted_defaults_to_zero_for_ordinary_drops(self):
        assert run("junk").dropped[0].details_omitted == 0
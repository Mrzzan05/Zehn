# Zehn Graph Context

Generated from Graphify. Component-based retrieval context.

## Overview

- Total graph nodes: 823
- Total graph edges: 606

## Components

### Extraction Pipeline

Purpose:
- Structural component extracted from Graphify.

Files:
- reality/extraction/__init__.py
- reality/extraction/audit.py
- reality/extraction/contracts.py
- reality/extraction/errors.py
- reality/extraction/normalization.py
- reality/extraction/pipeline.py
- reality/extraction/provider.py
- reality/extraction/validation.py

Core Symbols:
- AuditSink
- DroppedClaim
- ExtractionError
- ExtractionInternalError
- ExtractionMalformedOutput
- NormalizationMalformed
- NormalizationSuccess
- NormalizedClaim
- NullAuditSink
- Provider
- ValidationRejected
- ValidationSuccess
- extract()
- normalize()
- validate()

Related Components:
- Domain Schemas
- Orchestrator

Tests:
- See Test Coverage Map.

### Classification Layer

Purpose:
- Structural component extracted from Graphify.

Files:
- reality/classification/adapters.py
- reality/classification/contracts.py
- reality/classification/exceptions.py
- reality/classification/normalization.py
- reality/classification/pipeline.py
- reality/classification/schemas.py
- reality/classification/semantic_rules.py

Core Symbols:
- CandidateAttribute
- CandidateSubjectDescriptor
- ClassificationError
- ClassificationInternalError
- ClassificationObservation
- ClassificationProvider
- ClassificationResult
- DerivationMetadata
- DroppedProposal
- ErrorDetail
- MetadataEntry
- SemanticProposal
- TemporalMarker
- apply_semantic_rules()
- check_proposal()
- classify_observation()
- create_drop()
- normalize_classification()
- to_classification_observation()
- utc_now()

Related Components:
- Domain Schemas

Tests:
- See Test Coverage Map.

### Reality Engine

Purpose:
- Structural component extracted from Graphify.

Files:
- reality/engine.py

Core Symbols:
- AssertionContractViolation
- AssertionResult
- ContradictoryTypeField
- MissingTypeField
- UnsupportedAssertionType
- get_full_trace()
- process_assertion()
- process_observation()

Related Components:
- Database Layer
- Domain Schemas
- Orchestrator
- Repository Layer

Tests:
- See Test Coverage Map.

### Orchestrator

Purpose:
- Structural component extracted from Graphify.

Files:
- reality/orchestrator.py

Core Symbols:
- OrchestrationResult
- ingest_observation()

Related Components:
- Domain Schemas
- Extraction Pipeline
- Reality Engine

Tests:
- See Test Coverage Map.

### Repository Layer

Purpose:
- Structural component extracted from Graphify.

Files:
- reality/repository.py

Core Symbols:
- create_assertion()
- create_entity()
- create_observation()
- create_relationship()
- find_assertion()
- find_entity_by_name_and_type()
- get_assertion_by_id()
- get_entity_by_id()
- get_observation_by_id()
- get_relationship_by_assertion()
- get_relationships_for_entity()
- trace_relationship_to_observation()
- update_entity_attributes()

Related Components:
- Domain Schemas
- Reality Engine

Tests:
- See Test Coverage Map.

### Domain Schemas

Purpose:
- Structural component extracted from Graphify.

Files:
- reality/schemas.py

Core Symbols:
- Assertion
- Entity
- Observation
- Relationship
- ZehnBaseModel
- utc_now()

Related Components:
- Classification Layer
- Extraction Pipeline
- Orchestrator
- Reality Engine
- Repository Layer

Tests:
- See Test Coverage Map.

### Database Layer

Purpose:
- Structural component extracted from Graphify.

Files:
- reality/db.py

Core Symbols:
- get_connection()
- initialize_database()
- transaction()

Related Components:
- Reality Engine

Tests:
- See Test Coverage Map.

## Test Coverage Map

## Architecture Edges

- reality_bounded_snapshot_snapshot → reality_bounded_snapshot_project
- reality_classification_adapters_to_classification_observation → reality_classification_schemas_classificationobservation
- reality_classification_normalization_create_drop → reality_bounded_snapshot_snapshot
- reality_classification_normalization_create_drop → reality_classification_contracts_droppedproposal
- reality_classification_normalization_details_from_validation_error → reality_classification_contracts_errordetail
- reality_classification_normalization_details_from_validation_error → reality_classification_normalization_bound_loc
- reality_classification_normalization_is_json_domain → reality_classification_normalization_walk_domain
- reality_classification_normalization_normalize_classification → reality_classification_normalization_create_drop
- reality_classification_normalization_normalize_classification → reality_classification_normalization_is_json_domain
- reality_classification_normalization_normalize_classification → reality_classification_normalization_details_from_validation_error
- reality_classification_normalization_normalize_classification → reality_classification_contracts_errordetail
- reality_classification_normalization_normalize_classification → reality_classification_contracts_classificationresult
- reality_classification_pipeline_classify_observation → reality_classification_normalization_normalize_classification
- reality_classification_pipeline_classify_observation → reality_classification_semantic_rules_apply_semantic_rules
- reality_classification_pipeline_classify_observation → reality_classification_exceptions_classificationinternalerror
- reality_classification_semantic_rules_apply_semantic_rules → reality_classification_semantic_rules_check_proposal
- reality_classification_semantic_rules_apply_semantic_rules → reality_classification_normalization_create_drop
- reality_classification_semantic_rules_apply_semantic_rules → reality_classification_contracts_classificationresult
- reality_classification_semantic_rules_rule_descriptor → reality_classification_semantic_rules_blank
- reality_classification_semantic_rules_rule_descriptor → reality_classification_semantic_rules_violation
- reality_classification_semantic_rules_rule_object_text → reality_classification_semantic_rules_violation
- reality_classification_semantic_rules_rule_object_text → reality_classification_semantic_rules_blank
- reality_classification_semantic_rules_rule_predicate → reality_classification_semantic_rules_blank
- reality_classification_semantic_rules_rule_predicate → reality_classification_semantic_rules_violation
- reality_classification_semantic_rules_rule_temporal_markers → reality_classification_semantic_rules_blank
- reality_classification_semantic_rules_rule_temporal_markers → reality_classification_semantic_rules_violation
- reality_classification_semantic_rules_violation → reality_classification_contracts_errordetail
- reality_db_initialize_database → reality_db_get_connection
- reality_db_transaction → reality_db_get_connection
- reality_engine_apply_attribute → reality_repository_update_entity_attributes
- reality_engine_check_contract → reality_engine_unsupportedassertiontype
- reality_engine_check_contract → reality_engine_missingtypefield
- reality_engine_check_contract → reality_engine_contradictorytypefield
- reality_engine_get_full_trace → reality_db_transaction
- reality_engine_get_full_trace → reality_repository_trace_relationship_to_observation
- reality_engine_process_assertion → reality_repository_get_entity_by_id
- reality_engine_process_assertion → reality_engine_assertionresult
- reality_engine_process_assertion → reality_engine_apply_attribute
- reality_engine_process_assertion → reality_engine_check_contract
- reality_engine_process_assertion → reality_db_transaction
- reality_engine_process_assertion → reality_repository_find_assertion
- reality_engine_process_assertion → reality_engine_rebuild_result
- reality_engine_process_assertion → reality_repository_create_assertion
- reality_engine_process_assertion → reality_engine_resolve_or_create_entity
- reality_engine_process_assertion → reality_repository_create_relationship
- reality_engine_process_assertion → reality_schemas_relationship
- reality_engine_process_observation → reality_db_transaction
- reality_engine_process_observation → reality_repository_create_observation
- reality_engine_rebuild_result → reality_repository_find_entity_by_name_and_type
- reality_engine_rebuild_result → reality_repository_get_relationship_by_assertion

## Graph Rules

- Graph is navigation layer only.
- Runtime reality remains authoritative.
- Generated context must not modify architecture.

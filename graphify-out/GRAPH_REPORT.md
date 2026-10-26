# Graph Report - !zehn demo  (2026-10-08)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 823 nodes · 2254 edges · 39 communities (24 shown, 15 thin omitted)
- Extraction: 90% EXTRACTED · 10% INFERRED · 0% AMBIGUOUS · INFERRED: 217 edges (avg confidence: 0.93)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `14c8da2e`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Observation
- process_assertion
- repository.py
- run_one
- extract
- normalize
- ClassificationObservation
- test_bounded_snapshot.py
- DroppedClaim
- classify_observation
- test_pipeline_firewall.py
- validate
- TestSemanticFirewallBoundaries
- CandidateAttribute
- make
- classification/normalization.py
- extraction/test_pipeline.py
- Assertion
- test_immutability.py
- SemanticProposal
- orchestrator.py
- test_provider_errors.py
- extraction/contracts.py
- test_semantic_rules.py
- NormalizedClaim
- NullAuditSink
- TestMalformedRootAudit
- Provider
- ClassificationInternalError

## God Nodes (most connected - your core abstractions)
1. `Observation` - 65 edges
2. `extract()` - 54 edges
3. `ScriptedProvider` - 45 edges
4. `ingest_observation()` - 44 edges
5. `RecordingSink` - 41 edges
6. `Assertion` - 40 edges
7. `process_assertion()` - 38 edges
8. `DroppedClaim` - 37 edges
9. `SemanticProposal` - 34 edges
10. `run_one()` - 30 edges

## Surprising Connections (you probably didn't know these)
- `unpersisted_observation()` --uses--> `Observation`  [INFERRED]
  tests/extraction/test_pipeline.py → reality/schemas.py
- `valid_observation()` --uses--> `Observation`  [INFERRED]
  tests/extraction/test_pipeline.py → reality/schemas.py
- `RecordingSink` --uses--> `DroppedClaim`  [INFERRED]
  tests/support/recording_sink.py → reality/extraction/contracts.py
- `test_every_declaration_validation_rejects_the_engine_also_refuses()` --uses--> `AssertionContractViolation`  [INFERRED]
  tests/persistence/test_validation_engine_agreement.py → reality/engine.py
- `test_an_engine_contract_violation_aborts_the_rest_of_the_batch()` --uses--> `ContradictoryTypeField`  [INFERRED]
  tests/e2e/test_orchestrator.py → reality/engine.py

## Import Cycles
- None detected.

## Communities (39 total, 15 thin omitted)

### Community 0 - "Observation"
Cohesion: 0.06
Nodes (67): transaction(), AssertionResult, get_full_trace(), ingest_observation(), OrchestrationResult, Observation, _attr(), _count() (+59 more)

### Community 1 - "process_assertion"
Cohesion: 0.06
Nodes (37): get_connection(), initialize_database(), AssertionContractViolation, _check_contract(), ContradictoryTypeField, MissingTypeField, process_assertion(), process_observation() (+29 more)

### Community 2 - "repository.py"
Cohesion: 0.09
Nodes (36): _apply_attribute(), _rebuild_result(), _resolve_or_create_entity(), create_assertion(), create_entity(), create_observation(), create_relationship(), find_assertion() (+28 more)

### Community 3 - "run_one"
Cohesion: 0.06
Nodes (10): run(), run_one(), TestAcceptance, TestBoundedAudit, TestContainers, TestExactTypesOnly, TestJsonDomainGate, TestProvenance (+2 more)

### Community 4 - "extract"
Cohesion: 0.08
Nodes (4): extract(), TestDropProvenance, TestPipelineOrchestration, TestValidationDropProjection

### Community 5 - "normalize"
Cohesion: 0.08
Nodes (6): NormalizationSuccess, _format_error_paths(), normalize(), _safe_json_projection(), TestNormalizationDiscovery, TestStructuralMapping

### Community 6 - "ClassificationObservation"
Cohesion: 0.08
Nodes (8): to_classification_observation(), ClassificationProvider, ClassificationObservation, MetadataEntry, test_canonical_observation_is_projected_not_duplicated(), test_unpersisted_observation_is_refused(), observation(), TestObservationMetadata

### Community 7 - "test_bounded_snapshot.py"
Cohesion: 0.09
Nodes (13): snapshot(), Custom, MyDict, MyInt, MyStr, _canonical(), _imported_modules(), test_golden_snapshots_are_identical_to_the_pre_move_behavior() (+5 more)

### Community 8 - "DroppedClaim"
Cohesion: 0.11
Nodes (5): AuditSink, DroppedClaim, _CountingSink, TestDroppedClaim, TestResultTypes

### Community 9 - "classify_observation"
Cohesion: 0.19
Nodes (9): classify_observation(), clock(), FakeProvider, make_observation(), payload(), RaisingProvider, TestFailureModel, TestOutputHandling (+1 more)

### Community 10 - "test_pipeline_firewall.py"
Cohesion: 0.09
Nodes (8): DroppedProposal, clock(), MyDict, MyFloat, MyInt, MyStr, TestAuditContract, valid_payload()

### Community 11 - "validate"
Cohesion: 0.15
Nodes (4): validate(), _claim(), TestDeclaredKindAndTypes, TestValidationSemanticBoundary

### Community 12 - "TestSemanticFirewallBoundaries"
Cohesion: 0.12
Nodes (4): as_json_payload(), error_types(), TestDescriptorAndTemporalMarkers, TestSemanticFirewallBoundaries

### Community 13 - "CandidateAttribute"
Cohesion: 0.17
Nodes (8): CandidateAttribute, CandidateSubjectDescriptor, DerivationMetadata, TestProposalIsDeeplyImmutable, valid_derivation(), valid_descriptor(), valid_proposal(), TestDescriptor

### Community 14 - "make"
Cohesion: 0.19
Nodes (7): TemporalMarker, make(), rule_ids(), TestObjectText, TestPredicate, TestScopeBoundaries, TestTemporalMarkers

### Community 15 - "classification/normalization.py"
Cohesion: 0.13
Nodes (9): project(), _bound_loc(), create_drop(), _details_from_validation_error(), _is_json_domain(), normalize_classification(), utc_now(), _walk_domain() (+1 more)

### Community 16 - "extraction/test_pipeline.py"
Cohesion: 0.16
Nodes (8): ExtractionError, ExtractionInternalError, ExtractionMalformedOutput, _stamped(), provider(), sink(), unpersisted_observation(), valid_observation()

### Community 17 - "Assertion"
Cohesion: 0.16
Nodes (10): Assertion, utc_now(), fake_extract(), attribute(), _assertion_from(), _obs_id(), test_every_declaration_validation_rejects_the_engine_also_refuses(), test_everything_validation_admits_the_engine_accepts() (+2 more)

### Community 18 - "test_immutability.py"
Cohesion: 0.20
Nodes (5): contains_mutable_container(), models_defined_in(), test_every_model_is_frozen_strict_and_forbids_extras(), test_no_model_field_holds_a_mutable_container(), test_the_guard_detects_mutable_containers()

### Community 19 - "SemanticProposal"
Cohesion: 0.26
Nodes (9): ErrorDetail, SemanticProposal, _blank(), check_proposal(), _rule_descriptor(), _rule_object_text(), _rule_predicate(), _rule_temporal_markers() (+1 more)

### Community 20 - "orchestrator.py"
Cohesion: 0.20
Nodes (4): ProviderError, ProviderInvalidResponse, ProviderTimeout, ProviderUnavailable

### Community 21 - "test_provider_errors.py"
Cohesion: 0.16
Nodes (4): ClassificationError, _imported_modules(), test_dependency_direction(), test_provider_failures_form_one_neutral_family_outside_both_pipeline_families()

### Community 22 - "extraction/contracts.py"
Cohesion: 0.24
Nodes (4): NormalizationMalformed, ValidationRejected, ValidationSuccess, _reject()

### Community 23 - "test_semantic_rules.py"
Cohesion: 0.34
Nodes (4): ClassificationResult, apply_semantic_rules(), clock(), TestApplySemanticRules

## Knowledge Gaps
- **1 isolated node(s):** `Custom`
  These have ≤1 connection - possible missing edges. (Counts symbols only; 262 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `extract()` connect `extract` to `Observation`, `normalize`, `DroppedClaim`, `validate`, `classification/normalization.py`, `extraction/test_pipeline.py`, `Assertion`, `orchestrator.py`, `extraction/contracts.py`, `NullAuditSink`, `TestMalformedRootAudit`, `Provider`, `ClassificationInternalError`?**
  _High betweenness centrality (0.098) - this node is a cross-community bridge._
- **Are the 16 inferred relationships involving `Observation` (e.g. with `to_classification_observation()` and `process_observation()`) actually correct?**
  _`Observation` has 16 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Custom` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Observation` be split into smaller, more focused modules?**
  _Cohesion score 0.06383353905836713 - nodes in this community are weakly interconnected._
- **Why does `Observation` connect `Observation` to `process_assertion`, `repository.py`, `extract`, `ClassificationObservation`, `extraction/test_pipeline.py`, `Assertion`, `orchestrator.py`, `Provider`?**
  _High betweenness centrality (0.075) - this node is a cross-community bridge._
- **Are the 11 inferred relationships involving `extract()` (e.g. with `AuditSink` and `.record()`) actually correct?**
  _`extract()` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Should `process_assertion` be split into smaller, more focused modules?**
  _Cohesion score 0.0609009009009009 - nodes in this community are weakly interconnected._
"""Unit tests for the intent classifier (FR-008, FR-016, FR-025).

Tests derived from requirements, NOT from implementation code.
Each FR has at least one happy-path and one edge-case test.
"""

import pytest

from app.core.intent_classifier import (
    ClassificationResult,
    IntentResult,
    QueryType,
    classify_intent,
)


class TestConfidentialTopicDetection:
    """FR-016: Detect confidential HR matters and bypass RAG."""

    def test_harassment_detected(self) -> None:
        """UT-IC-003: 'harassment' triggers confidential classification."""
        result = classify_intent("I want to report harassment by my manager")
        assert result.intent == IntentResult.CONFIDENTIAL
        assert result.confidence >= 0.9
        assert len(result.detected_patterns) > 0

    def test_discrimination_detected(self) -> None:
        """UT-IC-004: 'discrimination' triggers confidential classification."""
        result = classify_intent("I'm experiencing discrimination at work")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_whistleblower_detected(self) -> None:
        """UT-IC-005: 'whistleblower' triggers confidential classification."""
        result = classify_intent("How do I file a whistleblower complaint?")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_sexual_harassment_detected(self) -> None:
        result = classify_intent("I need to report sexual harassment")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_hostile_work_environment_detected(self) -> None:
        result = classify_intent("I'm dealing with a hostile work environment")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_workplace_violence_detected(self) -> None:
        result = classify_intent("There's workplace violence in my department")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_ethics_violation_detected(self) -> None:
        result = classify_intent("I want to report an ethics violation")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_retaliation_detected(self) -> None:
        result = classify_intent("I'm experiencing retaliation for my complaint")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_report_manager_detected(self) -> None:
        result = classify_intent("How do I report my manager for misconduct?")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_filed_complaint_detected(self) -> None:
        result = classify_intent("I filed a complaint and nothing happened")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_unsafe_working_conditions_detected(self) -> None:
        result = classify_intent("We have unsafe working conditions on the floor")
        assert result.intent == IntentResult.CONFIDENTIAL

    def test_non_confidential_query_not_flagged(self) -> None:
        """Edge case: a normal policy question should NOT be classified as confidential."""
        result = classify_intent("What is the PTO policy?")
        assert result.intent != IntentResult.CONFIDENTIAL

    def test_confidential_takes_priority_over_escalation(self) -> None:
        """If a query matches both confidential and escalation, confidential wins."""
        result = classify_intent(
            "I need to talk to a person about harassment"
        )
        assert result.intent == IntentResult.CONFIDENTIAL


class TestEscalationRequestDetection:
    """FR-025: Detect explicit requests to escalate to a live agent."""

    def test_talk_to_a_person(self) -> None:
        """UT-IC-006: 'talk to a person' triggers escalation."""
        result = classify_intent("I want to talk to a person")
        assert result.intent == IntentResult.ESCALATION_REQUEST

    def test_speak_with_someone(self) -> None:
        """UT-IC-007: 'speak with someone' triggers escalation."""
        result = classify_intent("Can I speak with someone?")
        assert result.intent == IntentResult.ESCALATION_REQUEST

    def test_transfer_me(self) -> None:
        result = classify_intent("Please transfer me to an agent")
        assert result.intent == IntentResult.ESCALATION_REQUEST

    def test_escalate(self) -> None:
        result = classify_intent("I'd like to escalate this")
        assert result.intent == IntentResult.ESCALATION_REQUEST

    def test_real_person(self) -> None:
        result = classify_intent("Can I talk to a real person?")
        assert result.intent == IntentResult.ESCALATION_REQUEST

    def test_live_agent(self) -> None:
        result = classify_intent("I need live support please")
        assert result.intent == IntentResult.ESCALATION_REQUEST

    def test_normal_query_not_escalation(self) -> None:
        """Edge case: a normal query should NOT be classified as escalation."""
        result = classify_intent("What is the bereavement leave policy?")
        assert result.intent != IntentResult.ESCALATION_REQUEST


class TestQueryTypeClassification:
    """FR-008: Classify whether the query is procedural or factual."""

    def test_procedural_how_do_i(self) -> None:
        """UT-IC-001: 'How do I...' is classified as procedural."""
        result = classify_intent("How do I request parental leave?")
        assert result.intent == IntentResult.POLICY_QUESTION
        assert result.query_type == QueryType.PROCEDURAL

    def test_procedural_steps_to(self) -> None:
        result = classify_intent("What are the steps to get a parking badge?")
        assert result.query_type == QueryType.PROCEDURAL

    def test_procedural_process_for(self) -> None:
        result = classify_intent("What is the process for filing an expense?")
        assert result.query_type == QueryType.PROCEDURAL

    def test_procedural_submit(self) -> None:
        result = classify_intent("How do I submit a time-off request?")
        assert result.query_type == QueryType.PROCEDURAL

    def test_procedural_apply_for(self) -> None:
        result = classify_intent("How do I apply for tuition reimbursement?")
        assert result.query_type == QueryType.PROCEDURAL

    def test_factual_what_is(self) -> None:
        """UT-IC-002: 'What is...' without procedural keywords is factual."""
        result = classify_intent("What is the maximum number of PTO days?")
        assert result.intent == IntentResult.POLICY_QUESTION
        assert result.query_type == QueryType.FACTUAL

    def test_factual_when_is(self) -> None:
        result = classify_intent("When is the open enrollment period?")
        assert result.query_type == QueryType.FACTUAL

    def test_factual_who_is(self) -> None:
        result = classify_intent("Who is the head of HR?")
        assert result.query_type == QueryType.FACTUAL

    def test_classification_result_has_all_fields(self) -> None:
        """Verify the ClassificationResult dataclass is fully populated."""
        result = classify_intent("How do I request parental leave?")
        assert isinstance(result, ClassificationResult)
        assert isinstance(result.intent, IntentResult)
        assert isinstance(result.query_type, QueryType)
        assert isinstance(result.confidence, float)
        assert isinstance(result.detected_patterns, list)

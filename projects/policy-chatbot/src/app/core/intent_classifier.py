"""Intent classifier and confidential topic detector (FR-008, FR-016)."""

import re
from dataclasses import dataclass
from enum import StrEnum


class QueryType(StrEnum):
    """The type of information the employee is seeking."""

    PROCEDURAL = "procedural"
    FACTUAL = "factual"
    UNKNOWN = "unknown"


class IntentResult(StrEnum):
    """High-level classification of a user query."""

    POLICY_QUESTION = "policy_question"
    CONFIDENTIAL = "confidential"
    ESCALATION_REQUEST = "escalation_request"
    GREETING = "greeting"
    OFF_TOPIC = "off_topic"


# Patterns that indicate a confidential HR matter — bypass RAG entirely (FR-016)
CONFIDENTIAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\b(?:harass(?:ment|ed|ing)?)\b",
        r"\b(?:discriminat(?:ion|ed|ing)?)\b",
        r"\b(?:whistleblow(?:er|ing)?)\b",
        r"\b(?:retaliat(?:ion|ed|ing)?)\b",
        r"\b(?:sexual\s+(?:assault|misconduct|harassment))\b",
        r"\b(?:hostile\s+work\s+environment)\b",
        r"\b(?:workplace\s+(?:violence|bullying|intimidation))\b",
        r"\b(?:ethics?\s+(?:violation|complaint|hotline|report))\b",
        r"\b(?:report\s+(?:my\s+)?(?:manager|supervisor|boss))\b",
        r"\b(?:filed?\s+a\s+complaint)\b",
        r"\b(?:unsafe\s+working\s+conditions?)\b",
    ]
]

# Patterns for explicit escalation requests (FR-025)
ESCALATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\btalk\s+to\s+(?:a\s+)?(?:person|human|agent|someone|representative)\b",
        r"\bspeak\s+(?:to|with)\s+(?:a\s+)?(?:person|human|agent|someone)\b",
        r"\btransfer\s+(?:me|to)\b",
        r"\bescalate\b",
        r"\breal\s+person\b",
        r"\blive\s+(?:agent|support|help)\b",
        r"\bneed\s+(?:human\s+)?help\b",
    ]
]

# Procedural keywords — suggests the user wants a how-to checklist
PROCEDURAL_KEYWORDS: list[re.Pattern[str]] = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"\bhow\s+(?:do|can|to|should)\b",
        r"\bsteps?\s+(?:to|for)\b",
        r"\bprocess\s+(?:for|to|of)\b",
        r"\bprocedure\b",
        r"\brequest\s+(?:a|an|for|to)\b",
        r"\bapply\s+for\b",
        r"\bsubmit\b",
        r"\bfile\s+(?:a|an|for)\b",
        r"\bWhat\s+do\s+I\s+need\s+to\s+do\b",
    ]
]


@dataclass
class ClassificationResult:
    """Result of intent classification for a user query."""

    intent: IntentResult
    query_type: QueryType
    confidence: float
    detected_patterns: list[str]


def classify_intent(query: str) -> ClassificationResult:
    """Classify user intent and detect confidential topics before RAG.

    This runs BEFORE the retrieval pipeline so that confidential topics
    are caught and escalated without generating any AI response (FR-016).
    """
    # Check for confidential topics first — highest priority
    confidential_matches = [
        p.pattern for p in CONFIDENTIAL_PATTERNS if p.search(query)
    ]
    if confidential_matches:
        return ClassificationResult(
            intent=IntentResult.CONFIDENTIAL,
            query_type=QueryType.UNKNOWN,
            confidence=0.95,
            detected_patterns=confidential_matches,
        )

    # Check for explicit escalation requests
    escalation_matches = [
        p.pattern for p in ESCALATION_PATTERNS if p.search(query)
    ]
    if escalation_matches:
        return ClassificationResult(
            intent=IntentResult.ESCALATION_REQUEST,
            query_type=QueryType.UNKNOWN,
            confidence=0.95,
            detected_patterns=escalation_matches,
        )

    # Determine query type — procedural vs factual
    procedural_matches = [
        p.pattern for p in PROCEDURAL_KEYWORDS if p.search(query)
    ]
    query_type = QueryType.PROCEDURAL if procedural_matches else QueryType.FACTUAL

    return ClassificationResult(
        intent=IntentResult.POLICY_QUESTION,
        query_type=query_type,
        confidence=0.8,
        detected_patterns=procedural_matches,
    )

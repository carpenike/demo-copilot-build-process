"""Azure OpenAI service for LLM completions and embeddings.

Handles intent classification (GPT-4o-mini), answer generation (GPT-4o),
and embedding generation (text-embedding-3-large). Uses lazy imports so
the module is importable in CI without Azure credentials.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from app.config import Settings

logger = structlog.get_logger()

DISCLAIMER = (
    "This information is based on current corporate policy and is not legal advice. "
    "Policy details may have changed — verify the source document for the most current version."
)

SYSTEM_PROMPT_CLASSIFIER = """You are an intent classifier for a corporate policy chatbot.
Classify the user's query into:
1. domain: One of HR, IT, Finance, Facilities, Legal, Compliance, Safety, or null if unknown
2. type: One of "factual", "procedural", or "sensitive"

SENSITIVE queries include: harassment, discrimination, whistleblower, ethics violations,
complaints about managers, retaliation, or any topic requiring confidential HR handling.
If a query is sensitive, classify it immediately — do not attempt to answer.

Respond ONLY with JSON: {"domain": "...", "type": "...", "reasoning": "..."}"""

SYSTEM_PROMPT_ANSWER = """You are a corporate policy assistant. Answer the user's question
using ONLY the provided context from policy documents. Follow these rules strictly:

1. Answer ONLY from the provided context. If the context does not contain the answer,
   respond with: "I wasn't able to find a policy covering that topic."
2. For every claim, cite the source using this format:
   [Source: {document_title}, Section: {section_heading}, Effective: {effective_date}]
3. If the query is procedural (how-to), generate a numbered checklist of steps.
   For each step, classify it as "assisted" (system can help) or "manual" (user must do it).
4. Never provide legal advice. Never make up information not in the context.
5. Be concise and professional.

Respond with JSON:
{
  "answer": "your answer text",
  "citations": [{"document_title": "...", "section": "...", "effective_date": "...",
                  "source_url": "..."}],
  "checklist": null or {"steps": [{"step_number": 1, "text": "...", "type": "assisted|manual",
                                    "details": "...", "link": "...", "link_label": "..."}]},
  "confidence": 0.0-1.0
}"""


class LLMService:
    """Manages Azure OpenAI interactions for the RAG pipeline."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: Any = None

    def _get_client(self) -> Any:
        """Lazily initialize the Azure OpenAI client."""
        if self._client is None:
            from azure.identity import DefaultAzureCredential, get_bearer_token_provider
            from openai import AzureOpenAI

            credential = DefaultAzureCredential()
            token_provider = get_bearer_token_provider(
                credential, "https://cognitiveservices.azure.com/.default"
            )

            self._client = AzureOpenAI(
                azure_endpoint=self._settings.azure_openai_endpoint,
                api_version=self._settings.azure_openai_api_version,
                azure_ad_token_provider=token_provider,
            )
        return self._client

    async def classify_intent(
        self, query: str, conversation_context: list[dict[str, str]] | None = None
    ) -> dict[str, Any]:
        """Classify the user's intent using GPT-4o-mini.

        Returns dict with keys: domain, type, reasoning
        """
        client = self._get_client()

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT_CLASSIFIER},
        ]

        if conversation_context:
            messages.extend(conversation_context[-4:])

        messages.append({"role": "user", "content": query})

        response = client.chat.completions.create(
            model=self._settings.azure_openai_classifier_deployment,
            messages=messages,
            temperature=0.0,
            max_tokens=200,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        result: dict[str, Any] = json.loads(content)

        logger.info(
            "intent_classified",
            domain=result.get("domain"),
            intent_type=result.get("type"),
        )

        return result

    async def generate_answer(
        self,
        query: str,
        context_chunks: list[dict[str, Any]],
        conversation_context: list[dict[str, str]] | None = None,
        intent_type: str = "factual",
    ) -> dict[str, Any]:
        """Generate a grounded answer using GPT-4o with retrieved context.

        Returns dict with keys: answer, citations, checklist, confidence
        """
        client = self._get_client()

        context_text = self._format_context(context_chunks)

        prompt_addition = ""
        if intent_type == "procedural":
            prompt_addition = (
                "\n\nThe user is asking a procedural question. Generate a step-by-step checklist."
            )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT_ANSWER + prompt_addition},
        ]

        if conversation_context:
            messages.extend(conversation_context[-4:])

        messages.append(
            {
                "role": "user",
                "content": f"Context:\n{context_text}\n\nQuestion: {query}",
            }
        )

        response = client.chat.completions.create(
            model=self._settings.azure_openai_chat_deployment,
            messages=messages,
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content or "{}"
        result: dict[str, Any] = json.loads(content)

        logger.info(
            "answer_generated",
            confidence=result.get("confidence"),
            has_checklist=result.get("checklist") is not None,
            citation_count=len(result.get("citations", [])),
        )

        return result

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding for a text string."""
        client = self._get_client()

        response = client.embeddings.create(
            model=self._settings.azure_openai_embedding_deployment,
            input=text,
            dimensions=self._settings.azure_openai_embedding_dimensions,
        )

        return list(response.data[0].embedding)

    async def check_health(self) -> bool:
        """Verify Azure OpenAI is reachable by listing models."""
        try:
            client = self._get_client()
            client.models.list()
        except Exception:
            logger.warning("azure_openai_health_check_failed")
            return False
        else:
            return True

    def _format_context(self, chunks: list[dict[str, Any]]) -> str:
        """Format retrieved chunks into a context string for the LLM prompt."""
        parts: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            title = chunk.get("title", "Unknown")
            section = chunk.get("section_heading", "")
            effective = chunk.get("effective_date", "")
            source_url = chunk.get("source_url", "")
            content = chunk.get("content", "")

            header = f"[Document {i}: {title}"
            if section:
                header += f", Section: {section}"
            if effective:
                header += f", Effective: {effective}"
            if source_url:
                header += f", URL: {source_url}"
            header += "]"

            parts.append(f"{header}\n{content}")

        return "\n\n---\n\n".join(parts)

"""Azure OpenAI Service client wrapper for chat completion and embeddings."""

import json
import logging
from dataclasses import dataclass

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AsyncAzureOpenAI

from app.config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the Acme Corporation Policy Assistant. You answer employee questions \
about corporate policies using ONLY the provided policy document excerpts.

RULES:
1. Answer ONLY from the provided context. If no context is relevant, respond \
with exactly: NO_RELEVANT_POLICY
2. For every claim, include a citation in this format: \
[Source: {document_title}, §{section_heading}, effective {effective_date}]
3. If the question is procedural (how-to), respond with a JSON checklist using \
this schema:
{
  "type": "checklist",
  "answer": "brief intro text",
  "steps": [
    {
      "step": 1,
      "description": "step description",
      "type": "assisted|manual",
      "detail": "additional detail",
      "action": {"kind": "form_link|contact|scheduling|wayfinding", ...} // only for assisted
    }
  ],
  "citations": [
    {"document_title": "...", "section": "...",
     "effective_date": "...", "source_url": "..."}
  ]
}
4. If the question is factual (what/who/when), respond with plain text and \
citations at the end.
5. Be concise and professional. Do not speculate or provide personal opinions.
6. Never provide legal advice. You provide policy information only.
"""

DISCLAIMER = (
    "This information is based on current corporate policy and is not legal advice. "
    "Policy details may have changed — verify the source document for the most "
    "current version."
)


@dataclass
class ChatResponse:
    """Parsed response from Azure OpenAI chat completion."""

    content: str
    response_type: str  # "answer", "checklist", "no_match"
    citations: list[dict[str, str]]
    checklist: list[dict] | None  # type: ignore[type-arg]
    is_no_match: bool


class OpenAIService:
    """Wraps Azure OpenAI Service for chat completion and embedding generation."""

    def __init__(self, settings: Settings) -> None:
        token_provider = get_bearer_token_provider(
            DefaultAzureCredential(),
            "https://cognitiveservices.azure.com/.default",
        )
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=token_provider,
            api_version=settings.azure_openai_api_version,
        )
        self._chat_deployment = settings.azure_openai_chat_deployment
        self._embedding_deployment = settings.azure_openai_embedding_deployment
        self._embedding_dimensions = settings.azure_openai_embedding_dimensions

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a vector embedding for the given text."""
        response = await self._client.embeddings.create(
            input=text,
            model=self._embedding_deployment,
            dimensions=self._embedding_dimensions,
        )
        return response.data[0].embedding

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate vector embeddings for a batch of texts."""
        response = await self._client.embeddings.create(
            input=texts,
            model=self._embedding_deployment,
            dimensions=self._embedding_dimensions,
        )
        return [item.embedding for item in response.data]

    async def chat_completion(
        self,
        user_query: str,
        context_chunks: list[dict[str, str]],
        conversation_history: list[dict[str, str]],
    ) -> ChatResponse:
        """Generate a grounded RAG response from retrieved policy chunks."""
        context_text = "\n\n---\n\n".join(
            f"[Document: {c['document_title']}, §{c.get('section_heading', 'N/A')}, "
            f"effective {c.get('effective_date', 'N/A')}]\n{c['content']}"
            for c in context_chunks
        )

        messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"POLICY CONTEXT:\n\n{context_text}"},
        ]
        messages.extend(conversation_history)
        messages.append({"role": "user", "content": user_query})

        response = await self._client.chat.completions.create(
            model=self._chat_deployment,
            messages=messages,  # type: ignore[arg-type]
            temperature=0.1,
            max_tokens=2000,
        )

        raw_content = response.choices[0].message.content or ""
        return self._parse_response(raw_content, context_chunks)

    def _parse_response(
        self,
        raw_content: str,
        context_chunks: list[dict[str, str]],
    ) -> ChatResponse:
        """Parse the LLM output into a structured ChatResponse."""
        if "NO_RELEVANT_POLICY" in raw_content:
            return ChatResponse(
                content=(
                    "I wasn't able to find a policy covering that topic. "
                    "Would you like me to connect you with HR support?"
                ),
                response_type="no_match",
                citations=[],
                checklist=None,
                is_no_match=True,
            )

        # Attempt to parse as JSON checklist
        try:
            parsed = json.loads(raw_content)
            if isinstance(parsed, dict) and parsed.get("type") == "checklist":
                return ChatResponse(
                    content=parsed.get("answer", ""),
                    response_type="checklist",
                    citations=parsed.get("citations", []),
                    checklist=parsed.get("steps", []),
                    is_no_match=False,
                )
        except (json.JSONDecodeError, KeyError):
            pass

        # Plain text answer — extract citations from context chunks used
        citations = [
            {
                "document_title": c["document_title"],
                "section": c.get("section_heading", ""),
                "effective_date": c.get("effective_date", ""),
                "source_url": c.get("source_url", ""),
            }
            for c in context_chunks
        ]

        return ChatResponse(
            content=raw_content,
            response_type="answer",
            citations=citations,
            checklist=None,
            is_no_match=False,
        )

    async def is_available(self) -> bool:
        """Check if the Azure OpenAI endpoint is reachable."""
        try:
            # Use a minimal embeddings call to verify connectivity.
            # models.list() is not available on Azure OpenAI.
            await self._client.embeddings.create(
                input="health check",
                model=self._embedding_deployment,
                dimensions=self._embedding_dimensions,
            )
        except Exception as exc:
            logger.warning("Azure OpenAI Service is unavailable: %s", exc)
            return False
        else:
            return True

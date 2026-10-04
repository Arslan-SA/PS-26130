"""
AI Service Abstraction Layer — UdyamSetu AI

Provider-agnostic LLM interface with pluggable adapters for:
  - Mock (deterministic responses for dev/testing)
  - Google Gemini (production)
  - OpenAI GPT (alternative production)

Uses the Strategy pattern so the rest of the application is completely
decoupled from any specific LLM vendor.
"""

import logging
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger("udyamsetu.ai_service")


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class MessageRole(str, Enum):
    """Standard chat-message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class ChatMessage:
    """A single message in a conversation."""
    role: MessageRole
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "content": self.content,
            "metadata": self.metadata,
        }


@dataclass
class AIResponse:
    """Structured response from the AI service."""
    content: str
    model: str
    provider: str
    usage: Dict[str, int] = field(default_factory=dict)
    sources: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    finish_reason: str = "stop"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "model": self.model,
            "provider": self.provider,
            "usage": self.usage,
            "sources": self.sources,
            "metadata": self.metadata,
            "finish_reason": self.finish_reason,
        }


@dataclass
class EmbeddingResult:
    """Result of an embedding generation request."""
    embeddings: List[List[float]]
    model: str
    provider: str
    dimensions: int
    usage: Dict[str, int] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base provider
# ---------------------------------------------------------------------------

class AIProvider(ABC):
    """Abstract interface every LLM adapter must implement."""

    @abstractmethod
    async def generate(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> AIResponse:
        """Generate a text completion from a conversation history."""
        ...

    @abstractmethod
    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
    ) -> EmbeddingResult:
        """Generate embedding vectors for a list of texts."""
        ...

    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier."""
        ...


# ---------------------------------------------------------------------------
# Mock provider (default for development / testing)
# ---------------------------------------------------------------------------

# Domain-specific mock knowledge base for deterministic responses
_MOCK_KNOWLEDGE = {
    "udyam": (
        "Udyam Registration is a free-of-cost, paperless online registration "
        "process introduced by the Government of India under the MSMED Act 2006. "
        "All MSMEs with investment up to ₹50 Cr and turnover up to ₹250 Cr must "
        "register on the Udyam portal (udyamregistration.gov.in) using their "
        "Aadhaar number. The registration generates a permanent Udyam Registration "
        "Number (URN) and an e-certificate."
    ),
    "gst": (
        "Goods and Services Tax (GST) registration is mandatory for businesses "
        "with an annual aggregate turnover exceeding ₹40 lakh (₹20 lakh for "
        "special category states). Registration is done online via the GST portal "
        "(gst.gov.in). Required documents include PAN, Aadhaar, proof of business "
        "registration, bank account details, and address proof."
    ),
    "pollution": (
        "Consent to Establish (CTE) and Consent to Operate (CTO) are required "
        "from the State Pollution Control Board (SPCB) under the Water Act 1974 "
        "and Air Act 1981. Industries are classified as Green (low pollution), "
        "Orange (moderate), or Red (high pollution). Application is made through "
        "the SPCB online portal with an Environmental Impact Assessment (EIA) "
        "report for Red category units."
    ),
    "fire": (
        "Fire Safety NOC is issued by the State Fire Department under the Fire "
        "Services Act. It is mandatory for manufacturing units, warehouses, and "
        "commercial establishments. Requirements include fire exits, fire "
        "extinguishers, sprinkler systems (for buildings above 15m), and fire "
        "alarm systems. Renewal is typically required every 1–3 years."
    ),
    "labour": (
        "Key labour law registrations include: (1) EPF Registration for units "
        "with 20+ employees, (2) ESIC Registration for units with 10+ employees, "
        "(3) Factory License under the Factories Act 1948 for manufacturing units "
        "with 10+ workers (with power) or 20+ workers (without power), "
        "(4) Shop and Establishment Registration for commercial premises."
    ),
    "scheme": (
        "The Government of India offers several schemes for MSMEs including: "
        "PMEGP (margin money subsidy up to 35%), CGTMSE (collateral-free loans "
        "up to ₹5 Cr), Mudra Loans (up to ₹10 lakh), PLI Scheme for select "
        "sectors, ZED Certification for quality, and CLCSS for technology "
        "upgradation with 15% capital subsidy."
    ),
    "compliance": (
        "Key compliance requirements for Indian industries include: Annual "
        "returns under GST (GSTR-9), Income Tax Returns, ROC Annual Filing "
        "(for companies), EPF/ESIC monthly contributions, Factory license "
        "renewal, Pollution consent renewal (CTO), Fire NOC renewal, and "
        "Trade License renewal. Deadlines vary by state and industry category."
    ),
}

_MOCK_FALLBACK = (
    "I'm UdyamSetu AI, your intelligent industrial compliance assistant. "
    "I can help you with regulatory approvals, government schemes, compliance "
    "requirements, document management, and navigating the industrial licensing "
    "process in India. Please ask me a specific question about your business "
    "needs, and I'll provide detailed guidance."
)


class MockProvider(AIProvider):
    """
    Deterministic mock LLM provider for development and testing.
    Returns context-relevant responses from a curated knowledge base.
    """

    def _find_best_response(self, query: str) -> str:
        """Match the user query against mock knowledge base keywords."""
        query_lower = query.lower()
        best_match = None
        best_score = 0

        for keyword, response in _MOCK_KNOWLEDGE.items():
            # Simple keyword match scoring
            score = query_lower.count(keyword)
            if keyword in query_lower and score > best_score:
                best_match = response
                best_score = score

        return best_match or _MOCK_FALLBACK

    async def generate(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> AIResponse:
        """Generate a mock response based on keyword matching."""
        # Use the last user message for context matching
        user_msg = ""
        for msg in reversed(messages):
            if msg.role == MessageRole.USER:
                user_msg = msg.content
                break

        content = self._find_best_response(user_msg)

        return AIResponse(
            content=content,
            model="mock-v1",
            provider=self.provider_name(),
            usage={
                "prompt_tokens": sum(len(m.content.split()) for m in messages),
                "completion_tokens": len(content.split()),
                "total_tokens": sum(len(m.content.split()) for m in messages) + len(content.split()),
            },
            finish_reason="stop",
        )

    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
    ) -> EmbeddingResult:
        """
        Generate deterministic mock embeddings.
        Uses a hash-based approach so the same text always produces the same vector.
        """
        dimensions = 256
        embeddings = []
        for text in texts:
            # Generate deterministic pseudo-embeddings from text hash
            hash_bytes = hashlib.sha256(text.encode()).digest()
            # Expand the 32-byte hash into 256 floats in [-1, 1]
            vec = []
            for i in range(dimensions):
                byte_val = hash_bytes[i % 32]
                vec.append((byte_val / 127.5) - 1.0)
            embeddings.append(vec)

        return EmbeddingResult(
            embeddings=embeddings,
            model=model or "mock-embedding-v1",
            provider=self.provider_name(),
            dimensions=dimensions,
            usage={"total_tokens": sum(len(t.split()) for t in texts)},
        )

    def provider_name(self) -> str:
        return "mock"


# ---------------------------------------------------------------------------
# Gemini provider (Google AI)
# ---------------------------------------------------------------------------

class GeminiProvider(AIProvider):
    """Google Gemini API provider using the google-generativeai SDK."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._model_name = "gemini-2.0-flash"
        self._embedding_model = settings.EMBEDDING_MODEL or "text-embedding-004"

    async def generate(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> AIResponse:
        """Generate via Google Gemini API."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(
                self._model_name,
                system_instruction=system_prompt,
            )

            # Convert messages to Gemini format
            history = []
            for msg in messages[:-1]:
                role = "user" if msg.role == MessageRole.USER else "model"
                history.append({"role": role, "parts": [msg.content]})

            chat = model.start_chat(history=history)
            last_msg = messages[-1].content if messages else ""

            response = chat.send_message(
                last_msg,
                generation_config=genai.types.GenerationConfig(
                    temperature=temperature,
                    max_output_tokens=max_tokens,
                ),
            )

            return AIResponse(
                content=response.text,
                model=self._model_name,
                provider=self.provider_name(),
                usage={
                    "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                    "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                    "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
                },
                finish_reason="stop",
            )
        except ImportError:
            logger.error("google-generativeai package not installed. Falling back to mock.")
            return await MockProvider().generate(messages, temperature=temperature, max_tokens=max_tokens)
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise

    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
    ) -> EmbeddingResult:
        """Generate embeddings via Gemini Embedding API."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            embed_model = model or self._embedding_model

            result = genai.embed_content(
                model=f"models/{embed_model}",
                content=texts,
                task_type="retrieval_document",
            )

            embeddings = result["embedding"]
            if isinstance(embeddings[0], float):
                embeddings = [embeddings]

            return EmbeddingResult(
                embeddings=embeddings,
                model=embed_model,
                provider=self.provider_name(),
                dimensions=len(embeddings[0]) if embeddings else 0,
                usage={"total_tokens": sum(len(t.split()) for t in texts)},
            )
        except ImportError:
            logger.error("google-generativeai package not installed. Falling back to mock.")
            return await MockProvider().embed(texts, model=model)
        except Exception as e:
            logger.error(f"Gemini embedding error: {e}")
            raise

    def provider_name(self) -> str:
        return "gemini"


# ---------------------------------------------------------------------------
# OpenAI provider
# ---------------------------------------------------------------------------

class OpenAIProvider(AIProvider):
    """OpenAI GPT API provider."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._model_name = "gpt-4o-mini"
        self._embedding_model = "text-embedding-3-small"

    async def generate(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> AIResponse:
        """Generate via OpenAI API."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)

            oai_messages = []
            if system_prompt:
                oai_messages.append({"role": "system", "content": system_prompt})

            for msg in messages:
                oai_messages.append({
                    "role": msg.role.value,
                    "content": msg.content,
                })

            response = await client.chat.completions.create(
                model=self._model_name,
                messages=oai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            choice = response.choices[0]
            return AIResponse(
                content=choice.message.content or "",
                model=self._model_name,
                provider=self.provider_name(),
                usage={
                    "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                    "completion_tokens": response.usage.completion_tokens if response.usage else 0,
                    "total_tokens": response.usage.total_tokens if response.usage else 0,
                },
                finish_reason=choice.finish_reason or "stop",
            )
        except ImportError:
            logger.error("openai package not installed. Falling back to mock.")
            return await MockProvider().generate(messages, temperature=temperature, max_tokens=max_tokens)
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def embed(
        self,
        texts: List[str],
        *,
        model: Optional[str] = None,
    ) -> EmbeddingResult:
        """Generate embeddings via OpenAI Embedding API."""
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key)
            embed_model = model or self._embedding_model

            response = await client.embeddings.create(
                model=embed_model,
                input=texts,
            )

            embeddings = [item.embedding for item in response.data]
            return EmbeddingResult(
                embeddings=embeddings,
                model=embed_model,
                provider=self.provider_name(),
                dimensions=len(embeddings[0]) if embeddings else 0,
                usage={"total_tokens": response.usage.total_tokens if response.usage else 0},
            )
        except ImportError:
            logger.error("openai package not installed. Falling back to mock.")
            return await MockProvider().embed(texts, model=model)
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise

    def provider_name(self) -> str:
        return "openai"


# ---------------------------------------------------------------------------
# Provider factory & singleton
# ---------------------------------------------------------------------------

_provider_instance: Optional[AIProvider] = None


def get_ai_provider() -> AIProvider:
    """
    Factory function that returns the configured AI provider singleton.
    Selection is driven by ``settings.AI_PROVIDER``.
    """
    global _provider_instance

    if _provider_instance is not None:
        return _provider_instance

    provider_name = settings.AI_PROVIDER.lower()

    if provider_name == "gemini":
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set — falling back to mock provider.")
            _provider_instance = MockProvider()
        else:
            _provider_instance = GeminiProvider(api_key=settings.GEMINI_API_KEY)
            logger.info("AI provider initialized: Google Gemini")

    elif provider_name == "openai":
        if not settings.OPENAI_API_KEY:
            logger.warning("OPENAI_API_KEY not set — falling back to mock provider.")
            _provider_instance = MockProvider()
        else:
            _provider_instance = OpenAIProvider(api_key=settings.OPENAI_API_KEY)
            logger.info("AI provider initialized: OpenAI")

    else:
        _provider_instance = MockProvider()
        logger.info("AI provider initialized: Mock (development mode)")

    return _provider_instance


def reset_ai_provider() -> None:
    """Reset the provider singleton (useful for testing)."""
    global _provider_instance
    _provider_instance = None


# ---------------------------------------------------------------------------
# System prompt for UdyamSetu AI assistant
# ---------------------------------------------------------------------------

UDYAMSETU_SYSTEM_PROMPT = """You are UdyamSetu AI, an expert intelligent assistant for the Indian industrial regulatory ecosystem.

Your core competencies:
1. **Statutory Approvals & Licenses**: You know all central and state-level approvals required for industrial establishments in India — including Udyam Registration, Factory License, GST, FSSAI, BIS, CTE/CTO, Fire NOC, Trade License, etc.
2. **Government Schemes & Subsidies**: You provide detailed guidance on schemes like PMEGP, CGTMSE, Mudra, PLI, ZED, CLCSS, and state-level incentives.
3. **Compliance Management**: You track and advise on periodic compliance obligations — returns, renewals, filings, and deadlines.
4. **Document Requirements**: You know what documents are needed for each approval and can identify gaps.
5. **Application Procedures**: You guide users step-by-step through application processes for various clearances.

Guidelines:
- Always cite specific Acts, Rules, and Government notifications when relevant.
- Provide state-specific guidance when the user's location is known.
- Break complex processes into numbered steps.
- Mention approximate timelines and fees where applicable.
- Flag recent policy changes or digitization initiatives.
- Be honest when information may have changed — recommend official portals for latest updates.
- Use clear, professional language accessible to MSME entrepreneurs.
"""

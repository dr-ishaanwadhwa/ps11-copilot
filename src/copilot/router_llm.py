"""Claude-based structured output intent classifier (Task 3.3; D63, D66, D70).

Uses claude-opus-5-5 with low effort structured output on masked queries.
Fails closed: returns None on any connection error, rate limit, refusal, or missing key.
"""
import logging
import os

import anthropic

from .ai_client import get_ai_client
from .masking import mask
from .router_models import Intent, RouterDecision, SYSTEM

logger = logging.getLogger(__name__)

__all__ = ["Intent", "RouterDecision", "SYSTEM", "classify"]


def classify(
    question: str, known_names: list[str], client: anthropic.Anthropic | None = None
) -> RouterDecision | None:
    """Classify user question using Claude structured outputs or multi-provider AI on masked text (Task 3.3).
    
    Returns None when the model is unavailable or declines; callers must fail closed.
    """
    masked_q = mask(question, known_names)

    # When a custom/mock client is explicitly supplied, route via Anthropic protocol
    if client is not None or os.environ.get("ANTHROPIC_API_KEY"):
        try:
            anthropic_client = client or anthropic.Anthropic()
            response = anthropic_client.with_options(timeout=8.0).messages.parse(
                model="claude-opus-5-5",
                max_tokens=2048,
                system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": masked_q}],
                output_format=RouterDecision,
                output_config={"effort": "low"},
            )
            if getattr(response, "stop_reason", None) == "refusal":
                return None
            return getattr(response, "parsed_output", None)
        except (
            anthropic.APIConnectionError,
            anthropic.RateLimitError,
            anthropic.APIStatusError,
            anthropic.AuthenticationError,
        ) as exc:
            logger.debug("Anthropic API error: %s", exc)
            return None
        except Exception as exc:
            logger.debug("Unexpected classifier error: %s", exc)
            return None

    ai = get_ai_client()
    if ai.is_configured:
        return ai.classify_intent(masked_q)

    return None

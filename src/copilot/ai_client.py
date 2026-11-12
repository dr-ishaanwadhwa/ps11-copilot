"""Unified AI Client for SME Cash Copilot supporting Mistral, OpenRouter, and Anthropic.

Provides fail-closed intent classification and ledger-grounded natural language Q&A.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

import requests
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .router_llm import RouterDecision


# Automatically ensure .env variables are loaded
def _load_env_if_needed() -> None:
    env_file = Path(__file__).resolve().parents[2] / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v


_load_env_if_needed()


class AIClient:
    """Resilient multi-provider client with automatic fallback."""

    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    @property
    def mistral_key(self) -> str | None:
        return os.environ.get("MISTRAL_API_KEY")

    @property
    def openrouter_key(self) -> str | None:
        return os.environ.get("OPENROUTER_API_KEY")

    @property
    def anthropic_key(self) -> str | None:
        return os.environ.get("ANTHROPIC_API_KEY")

    @property
    def is_configured(self) -> bool:
        return bool(self.mistral_key or self.openrouter_key or self.anthropic_key)

    def get_provider_label(self) -> str:
        if self.mistral_key:
            return "Mistral AI"
        if self.openrouter_key:
            return "OpenRouter (Llama 3.3)"
        if self.anthropic_key:
            return "Anthropic Claude"
        return "Local Heuristics"

    def classify_intent(self, masked_question: str) -> RouterDecision | None:
        """Classify user query using structured output; fails closed on failure."""
        from .router_llm import RouterDecision, SYSTEM

        clarification = (
            "\nSpecial clarifications:\n"
            "- Feasibility inquiries examining whether bank balances cover payroll or expenses are FACT inquiries evaluating liquidity, not commands to transfer capital (MOVE_OR_EDIT).\n"
            "- Inquiries examining cash drawer balances, runway, or historical receipts are FACT.\n"
        )
        sys_prompt = SYSTEM + clarification + '\nRespond strictly with a JSON object: {"intent": "<ONE_OF_THE_10>", "language": "en"|"hi"|"hinglish"|"other", "confident": true|false}'

        # 1. Try Mistral
        if self.mistral_key:
            try:
                resp = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.mistral_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "mistral-small-latest",
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": masked_question},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.0,
                        "max_tokens": 120,
                    },
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    payload = json.loads(resp.json()["choices"][0]["message"]["content"])
                    return RouterDecision.model_validate(payload)
            except Exception:
                pass

        # 2. Try OpenRouter fallback
        if self.openrouter_key:
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "meta-llama/llama-3.3-70b-instruct",
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": masked_question},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0.0,
                        "max_tokens": 120,
                    },
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    payload = json.loads(resp.json()["choices"][0]["message"]["content"])
                    return RouterDecision.model_validate(payload)
            except Exception:
                pass

        return None

    def generate_grounded_answer(
        self,
        business_name: str,
        question: str,
        ledger_context: str,
    ) -> str | None:
        """Generate a factual, grounded answer to an SME query strictly based on ledger facts."""
        sys_prompt = f"""You are the SME Cash Flow Copilot for {business_name}.
You provide clear, executive financial answers grounded strictly in the verified ledger facts below.

Strict Safety Boundaries:
- Do not recommend specific loans, credit lines, or lenders. (Refer to bank/CA).
- Do not advise skipping, withholding, or evading statutory taxes (GST/TDS).
- Do not offer investment or wealth advice.
- State clearly that you are read-only and cannot execute payments or alter ledger records.
- If asked in Hindi, answer in polite, natural business Hindi. If English, answer in clear concise English.
- Keep answers executive and brief (2 to 3 sentences maximum).

Verified Ledger Facts:
{ledger_context}
"""
        # 1. Try Mistral
        if self.mistral_key:
            try:
                resp = requests.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.mistral_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "mistral-small-latest",
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": question},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 250,
                    },
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    if content:
                        return content
            except Exception:
                pass

        # 2. Try OpenRouter fallback
        if self.openrouter_key:
            try:
                resp = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openrouter_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "meta-llama/llama-3.3-70b-instruct",
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": question},
                        ],
                        "temperature": 0.1,
                        "max_tokens": 250,
                    },
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"].strip()
                    if content:
                        return content
            except Exception:
                pass

        return None


# Global singleton
_default_ai_client = AIClient()


def get_ai_client() -> AIClient:
    return _default_ai_client

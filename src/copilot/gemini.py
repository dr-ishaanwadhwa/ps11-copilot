"""Gemini 3.5 Multimodal Client for Voice Transcription and Slip Vision OCR."""
from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any

import requests

from .ai_client import _load_env_if_needed

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
GEMINI_MODEL = "gemini-3.5-flash"


def _get_api_key() -> str | None:
    _load_env_if_needed()
    return os.getenv("GEMINI_API_KEY")


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """Transcribe spoken audio bytes into a question string using Gemini 3.5."""
    api_key = _get_api_key()
    if not api_key:
        logger.warning("GEMINI_API_KEY not configured; cannot transcribe audio.")
        return ""

    b64_audio = base64.b64encode(audio_bytes).decode("utf-8")
    url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent?key={api_key}"
    prompt = (
        "You are an expert transcriber for an Indian SME cash-flow application. "
        "The speaker may speak in English, Hindi, or Hinglish (e.g. asking 'Can I pay salaries?', "
        "'Sabse zyada udhari kis par hai?', 'Kya kal check clear hoga?'). "
        "Transcribe the audio accurately. Return ONLY the transcribed text string, without quotes or explanations."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_audio,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 200,
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    return parts[0].get("text", "").strip()
        logger.warning("Gemini audio transcription failed: status %s %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Gemini audio transcription error: %s", exc)
    return ""


def _extract_json(raw_text: str) -> dict[str, Any]:
    """Robustly parse JSON object from markdown code fences or text with preambles."""
    text = raw_text.strip()
    if not text:
        return {}

    # 1. Direct parse
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 2. Markdown code fences: ```json ... ``` or ``` ... ```
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        try:
            obj = json.loads(fence.group(1).strip())
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # 3. Balanced brace search (handles preambles containing curly braces like "{slip #42}")
    brace_indices = [m.start() for m in re.finditer(r"\{", text)]
    for start in brace_indices:
        end = text.rfind("}")
        while end > start:
            candidate = text[start : end + 1]
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except Exception:
                end = text.rfind("}", start, end)

    # 4. Bare key-value pairs without enclosing braces
    if "{" not in text and ":" in text:
        try:
            obj = json.loads("{" + text + "}")
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    # 5. Greedy fallback
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if json_match:
        try:
            obj = json.loads(json_match.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass

    return {}


def ocr_collection_slip(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict[str, Any]:
    """Extract structured data from a photographed collection slip using Gemini Vision.

    Returns dict with keys:
        - retailer_name: str (Shop or retailer name)
        - shop: str (Alias for retailer_name for backward compatibility)
        - amount: float (Rupees collected)
        - payment_mode: str ("Cash", "UPI", or "Cheque")
        - salesman: str (Salesman or agent name)
        - date: str (YYYY-MM-DD or empty)
        - slip_no: str (Slip or receipt number)
        - confidence: float (0.0 to 1.0)
        - notes: str
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("GEMINI_API_KEY not configured; using offline fallback parser.")
        return {
            "retailer_name": "Sample Retailer",
            "shop": "Sample Retailer",
            "amount": 10000.0,
            "payment_mode": "Cash",
            "salesman": "Field Agent",
            "date": "2026-09-30",
            "slip_no": "SLIP-001",
            "confidence": 0.95,
            "notes": "No API key (offline mock)",
        }

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent?key={api_key}"
    prompt = (
        "You are an expert OCR system for Indian SME salesman collection slips, receipts, and deposit memos. "
        "Extract the following fields from this image and return ONLY a valid JSON object with these keys:\n"
        "{\n"
        '  "retailer_name": "<Shop or retailer name>",\n'
        '  "amount": <Total rupee amount as a numeric float, without currency symbols>,\n'
        '  "payment_mode": "<Payment mode: Cash, UPI, or Cheque>",\n'
        '  "salesman": "<Salesman or collector name, or empty string if not found>",\n'
        '  "date": "<YYYY-MM-DD format if date is visible, or empty string>",\n'
        '  "slip_no": "<Slip or receipt number if visible, or empty string>",\n'
        '  "confidence": <Confidence score between 0.0 and 1.0 as float>,\n'
        '  "notes": "<Brief description of handwritten markings or receipt details>"\n'
        "}\n"
        "If multiple shops are on one slip, pick the primary one or largest amount. Do not include markdown fences.\n"
        "If the shop name is handwritten in Hindi/Devanagari, provide the Latin English transliteration (e.g., 'Laxmi Kirana Stores') in the retailer_name field."
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": b64_image,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.1,
            "maxOutputTokens": 300,
        },
    }

    try:
        resp = requests.post(url, json=payload, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts:
                    raw_text = parts[0].get("text", "").strip()
                    # Clean markdown code fences or conversational wrapping via robust JSON extractor
                    parsed = _extract_json(raw_text)
                    if not parsed:
                        raise ValueError(f"Could not extract valid JSON from Gemini Vision response: {raw_text[:100]}")

                    retailer = str(parsed.get("retailer_name") or parsed.get("shop") or "").strip()
                    raw_mode = str(parsed.get("payment_mode") or "Cash").strip()
                    mode_upper = raw_mode.upper()
                    if "UPI" in mode_upper:
                        payment_mode = "UPI"
                    elif "CHEQ" in mode_upper or "CHQ" in mode_upper:
                        payment_mode = "Cheque"
                    else:
                        payment_mode = "Cash"

                    try:
                        confidence = float(parsed.get("confidence", 0.95))
                        confidence = max(0.0, min(1.0, confidence))
                    except (ValueError, TypeError):
                        confidence = 0.85

                    raw_amt = parsed.get("amount", 0.0) or 0.0
                    if isinstance(raw_amt, str):
                        s = re.sub(r"(?i)\b(?:rs\.?|inr|rupees?)\b\.?|₹", "", raw_amt)
                        cleaned_amt = re.sub(r"[^\d.]", "", s).strip(".")
                        try:
                            amount = float(cleaned_amt) if cleaned_amt else 0.0
                        except (ValueError, TypeError):
                            amount = 0.0
                    else:
                        try:
                            amount = float(raw_amt)
                        except (ValueError, TypeError):
                            amount = 0.0

                    return {
                        "retailer_name": retailer,
                        "shop": retailer,
                        "amount": amount,
                        "payment_mode": payment_mode,
                        "salesman": str(parsed.get("salesman", "")).strip(),
                        "date": str(parsed.get("date", "")).strip(),
                        "slip_no": str(parsed.get("slip_no", "")).strip(),
                        "confidence": confidence,
                        "notes": str(parsed.get("notes", "")).strip(),
                    }
        logger.warning("Gemini Vision OCR failed: status %s %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Gemini Vision OCR error: %s", exc)

    return {
        "retailer_name": "",
        "shop": "",
        "amount": 0.0,
        "payment_mode": "Cash",
        "salesman": "",
        "date": "",
        "slip_no": "",
        "confidence": 0.0,
        "notes": "OCR extraction failed",
    }

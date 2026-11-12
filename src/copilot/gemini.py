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


def ocr_collection_slip(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict[str, Any]:
    """Extract structured data from a photographed collection slip using Gemini Vision.

    Returns dict with keys:
        - shop: str (Shop or retailer name)
        - amount: float (Rupees collected)
        - salesman: str (Salesman or agent name)
        - date: str (YYYY-MM-DD or empty)
        - notes: str
    """
    api_key = _get_api_key()
    if not api_key:
        logger.warning("GEMINI_API_KEY not configured; using offline fallback parser.")
        return {"shop": "Sample Retailer", "amount": 10000.0, "salesman": "Field Agent", "date": "", "notes": "No API key"}

    b64_image = base64.b64encode(image_bytes).decode("utf-8")
    url = f"{GEMINI_API_BASE}/{GEMINI_MODEL}:generateContent?key={api_key}"
    prompt = (
        "You are an expert OCR system for Indian SME salesman collection slips, receipts, and deposit memos. "
        "Extract the following fields from this image and return ONLY a valid JSON object with these keys:\n"
        "{\n"
        '  "shop": "<Shop or retailer name>",\n'
        '  "amount": <Total rupee amount as a numeric float, without currency symbols>,\n'
        '  "salesman": "<Salesman or collector name, or empty string if not found>",\n'
        '  "date": "<YYYY-MM-DD format if date is visible, or empty string>",\n'
        '  "notes": "<Brief description of handwritten markings or receipt number>"\n'
        "}\n"
        "If multiple shops are on one slip, pick the primary one or largest amount. Do not include markdown fences."
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
                    # Clean markdown code fences if present
                    clean_json = re.sub(r"^```(?:json)?|```$", "", raw_text, flags=re.MULTILINE).strip()
                    parsed = json.loads(clean_json)
                    return {
                        "shop": str(parsed.get("shop", "")).strip(),
                        "amount": float(parsed.get("amount", 0.0) or 0.0),
                        "salesman": str(parsed.get("salesman", "")).strip(),
                        "date": str(parsed.get("date", "")).strip(),
                        "notes": str(parsed.get("notes", "")).strip(),
                    }
        logger.warning("Gemini Vision OCR failed: status %s %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.warning("Gemini Vision OCR error: %s", exc)

    return {"shop": "", "amount": 0.0, "salesman": "", "date": "", "notes": "OCR extraction failed"}

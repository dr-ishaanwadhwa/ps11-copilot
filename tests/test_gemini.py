"""Tests for Gemini Multimodal voice transcription and Vision OCR."""
import json
from unittest.mock import MagicMock, patch

from copilot.gemini import ocr_collection_slip, transcribe_audio


def test_transcribe_audio_mocked():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Can I pay salaries on 1 October?"}]
                }
            }
        ]
    }

    with patch("copilot.gemini.requests.post", return_value=fake_response):
        with patch("copilot.gemini._get_api_key", return_value="fake-key"):
            res = transcribe_audio(b"fake_audio_bytes", mime_type="audio/wav")
            assert res == "Can I pay salaries on 1 October?"


def test_ocr_collection_slip_mocked():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_json = {
        "shop": "Laxmi Kirana Stores",
        "amount": 15000.0,
        "salesman": "Ramesh K.",
        "date": "2026-09-30",
        "notes": "Slip #104"
    }
    fake_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": f"```json\n{json.dumps(fake_json)}\n```"}]
                }
            }
        ]
    }

    with patch("copilot.gemini.requests.post", return_value=fake_response):
        with patch("copilot.gemini._get_api_key", return_value="fake-key"):
            res = ocr_collection_slip(b"fake_image_bytes", mime_type="image/jpeg")
            assert res["shop"] == "Laxmi Kirana Stores"
            assert res["amount"] == 15000.0
            assert res["salesman"] == "Ramesh K."
            assert res["date"] == "2026-09-30"


def test_ocr_fallback_on_no_api_key():
    with patch("copilot.gemini._get_api_key", return_value=None):
        res = ocr_collection_slip(b"fake_image")
        assert "shop" in res
        assert "amount" in res

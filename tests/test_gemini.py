"""Tests for Gemini Multimodal voice transcription and Vision OCR."""
import json
from unittest.mock import MagicMock, patch

import pytest

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


def test_ocr_collection_slip_expanded_schema():
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_json = {
        "retailer_name": "Balaji Provision Stores",
        "amount": 24500.0,
        "payment_mode": "UPI",
        "salesman": "Vijay Patil",
        "date": "2026-09-30",
        "slip_no": "SLIP-UPI-88",
        "confidence": 0.94,
        "notes": "Route clearance"
    }
    fake_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(fake_json)}]
                }
            }
        ]
    }

    with patch("copilot.gemini.requests.post", return_value=fake_response):
        with patch("copilot.gemini._get_api_key", return_value="fake-key"):
            res = ocr_collection_slip(b"fake_image_bytes", mime_type="image/jpeg")
            assert res["retailer_name"] == "Balaji Provision Stores"
            assert res["shop"] == "Balaji Provision Stores"
            assert res["amount"] == 24500.0
            assert res["payment_mode"] == "UPI"
            assert res["salesman"] == "Vijay Patil"
            assert res["date"] == "2026-09-30"
            assert res["slip_no"] == "SLIP-UPI-88"
            assert res["confidence"] == 0.94
            assert res["notes"] == "Route clearance"


def test_ocr_collection_slip_offline_fallback_contains_all_keys():
    with patch("copilot.gemini._get_api_key", return_value=None):
        res = ocr_collection_slip(b"fake_image")
        for key in ["retailer_name", "shop", "amount", "payment_mode", "salesman", "date", "slip_no", "confidence", "notes"]:
            assert key in res, f"Expected {key} in offline fallback dict"
        assert res["retailer_name"] == "Sample Retailer"
        assert res["shop"] == "Sample Retailer"
        assert res["payment_mode"] == "Cash"
        assert isinstance(res["confidence"], float)


def test_ocr_collection_slip_conversational_markdown_and_currency_sanitization():
    """Verify Gemini OCR extracts cleanly from conversational preamble/postamble and handles comma/rupee strings."""
    conversational_text = """Here is the extracted JSON for the collection slip:
```json
{
  "retailer_name": "Laxmi Kirana Stores",
  "amount": "₹15,000",
  "payment_mode": "Cash",
  "salesman": "Ramesh",
  "date": "2026-09-30"
}
```
Hope this helps! Feel free to ask if you need further clarification."""

    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": conversational_text}]
                }
            }
        ]
    }

    with patch("copilot.gemini.requests.post", return_value=fake_response):
        with patch("copilot.gemini._get_api_key", return_value="fake-key"):
            res = ocr_collection_slip(b"fake_image_bytes", mime_type="image/jpeg")
            assert res["retailer_name"] == "Laxmi Kirana Stores"
            assert res["amount"] == 15000.0
            assert res["confidence"] > 0.0


@pytest.mark.parametrize(
    "raw_amt_str,expected_amount",
    [
        ("Rs. 25,000/-", 25000.0),
        ("Rs. 15,000.50", 15000.5),
        ("₹15,000", 15000.0),
        ("15,000", 15000.0),
        ("INR 1,50,000.75", 150000.75),
        ("Rupees 500", 500.0),
        ("Rs 25000", 25000.0),
    ],
)
def test_ocr_collection_slip_currency_formats(raw_amt_str, expected_amount):
    """Verify Indian currency string prefixes and formats correctly parse to float amounts."""
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_json = {
        "retailer_name": "Laxmi Kirana",
        "amount": raw_amt_str,
        "payment_mode": "Cash",
    }
    fake_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(fake_json)}]
                }
            }
        ]
    }

    with patch("copilot.gemini.requests.post", return_value=fake_response):
        with patch("copilot.gemini._get_api_key", return_value="fake-key"):
            res = ocr_collection_slip(b"fake_image_bytes")
            assert res["retailer_name"] == "Laxmi Kirana"
            assert res["amount"] == expected_amount
            assert res["confidence"] > 0.0


def test_ocr_collection_slip_preamble_with_curly_braces():
    """Verify conversational preambles containing curly braces outside JSON do not corrupt parsing."""
    raw_text = 'I checked {slip #42} and found: {"retailer_name": "Laxmi Kirana", "amount": "Rs. 15,000.50"}'
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": raw_text}]
                }
            }
        ]
    }

    with patch("copilot.gemini.requests.post", return_value=fake_response):
        with patch("copilot.gemini._get_api_key", return_value="fake-key"):
            res = ocr_collection_slip(b"fake_image_bytes")
            assert res["retailer_name"] == "Laxmi Kirana"
            assert res["amount"] == 15000.5
            assert res["confidence"] > 0.0




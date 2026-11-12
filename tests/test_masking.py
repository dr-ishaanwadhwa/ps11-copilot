"""Unit tests for privacy masking (Task 3.2)."""
import pytest
from copilot.masking import mask


def test_mask_party_names():
    known = ["Acme Corp", "Acme", "Beta Enterprises"]
    # Longest match first: "Acme Corp" should be Party 1, not Party 2 + "Corp"
    s = "Send invoice to Acme Corp and also to Beta Enterprises."
    masked = mask(s, known)
    assert "Acme Corp" not in masked
    assert "Beta Enterprises" not in masked
    assert "Party 1" in masked
    assert "Party 2" in masked


def test_mask_party_names_stability_within_call():
    known = ["Ramesh Stores"]
    s = "Ramesh Stores owes money, remind Ramesh Stores today."
    masked = mask(s, known)
    assert masked == "Party 1 owes money, remind Party 1 today."


def test_mask_gstin():
    s = "Customer GSTIN is 27AABCU9603R1ZN."
    assert mask(s) == "Customer GSTIN is [GSTIN]."


def test_mask_pan():
    s = "Vendor PAN is ABCDE1234F for filing."
    assert mask(s) == "Vendor PAN is [PAN] for filing."


def test_mask_email_and_upi():
    s = "Pay via payments@hdfcbank or contact user@example.com."
    assert mask(s) == "Pay via [ID] or contact [ID]."


def test_mask_long_digits():
    s = "Account number 123456789012 or phone 9876543210."
    assert mask(s) == "Account number [NUMBER] or phone [NUMBER]."


def test_mask_rupee_amounts():
    s = "Transfer ₹50,000 and Rs. 1,20,500.50 or INR 10000."
    assert mask(s) == "Transfer ₹[AMOUNT] and ₹[AMOUNT] or ₹[AMOUNT]."


def test_mask_clean_sentence_unchanged():
    s = "Can I pay salaries on time this month?"
    assert mask(s) == s

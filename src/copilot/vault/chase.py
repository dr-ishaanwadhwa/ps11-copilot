"""Confidential informal credit chasing and statutory limitation management.

In accordance with:
- Limitation Act, 1963 Section 18 (signed electronic acknowledgment resets the 3-year debt clock).
- DPDP Rules, 2025 (local-only wa.me deep links without uploading customer phone books to cloud BSPs).
- Friendly vernacular copy avoiding corporate or aggressive debt collection language.
"""
from __future__ import annotations

import urllib.parse
from .models import KhataAccount


def format_whatsapp_reminder(account: KhataAccount, business_name: str, upi_handle: str = "") -> dict:
    """
    Generates a polite, non-incriminating client-side WhatsApp draft.
    Does not send anything automatically; generates a wa.me URL for the owner to review and tap.
    """
    amount_str = f"₹{account.balance_due:,.0f}"
    
    if account.is_limitation_alert:
        # Subtle Section 18 acknowledgment request without sounding legalistic
        text = (
            f"Namaste {account.party_name} ji, hope you are doing well. As per our records with {business_name}, "
            f"the pending balance is {amount_str} from our earlier supplies. Could you please confirm if this matches "
            f"your books, or let us know when we can expect a small part-settlement? Thank you!"
        )
    else:
        text = (
            f"Namaste {account.party_name} ji, warm greetings from {business_name}. "
            f"Just sharing a friendly update: your current pending khata balance is {amount_str}. "
            f"Whenever convenient, please arrange the settlement{f' via UPI to {upi_handle}' if upi_handle else ''}. "
            f"Thank you for your partnership!"
        )

    encoded_text = urllib.parse.quote(text)
    clean_phone = "".join(ch for ch in account.phone if ch.isdigit())
    if len(clean_phone) == 10:
        clean_phone = "91" + clean_phone
        
    wa_url = f"https://wa.me/{clean_phone}?text={encoded_text}" if clean_phone else f"https://wa.me/?text={encoded_text}"
    
    return {
        "party_name": account.party_name,
        "amount": account.balance_due,
        "draft_message": text,
        "wa_link": wa_url,
        "limitation_warning": (
            "This balance is over 30 months old. A written acknowledgement from the customer may keep it recoverable; your CA or lawyer can confirm."
            if account.is_limitation_alert else None
        )
    }

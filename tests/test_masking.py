import io
from PIL import Image
import pytest
from copilot.masking import mask, sanitize_slip_image


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


def test_sanitize_slip_image_strips_exif_metadata():
    """Verify that sanitize_slip_image removes all EXIF and camera metadata."""
    img = Image.new("RGB", (120, 80), color="blue")
    exif = Image.Exif()
    exif[271] = "Canon"  # Make
    exif[272] = "EOS Rebel T7"  # Model
    exif[305] = "Firmware 1.0.0"  # Software
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    dirty_bytes = buf.getvalue()

    # Confirm EXIF exists before sanitization
    pre_img = Image.open(io.BytesIO(dirty_bytes))
    assert len(dict(pre_img.getexif())) > 0

    # Sanitize
    clean_bytes = sanitize_slip_image(dirty_bytes)
    post_img = Image.open(io.BytesIO(clean_bytes))
    assert len(dict(post_img.getexif())) == 0
    assert post_img.size == (120, 80)
    assert post_img.format == "JPEG"


def test_sanitize_slip_image_handles_corrupt_or_empty_bytes():
    """Verify that corrupted or empty inputs are safely handled without throwing exceptions."""
    assert sanitize_slip_image(b"") == b""
    corrupt = b"not_an_image_binary_data_123456"
    assert sanitize_slip_image(corrupt) == corrupt


def test_sanitize_slip_image_preserves_png():
    """Verify that PNG format is cleanly processed."""
    png_img = Image.new("RGBA", (60, 40), color=(0, 255, 0, 128))
    buf = io.BytesIO()
    png_img.save(buf, format="PNG")
    clean_png = sanitize_slip_image(buf.getvalue())
    post_png = Image.open(io.BytesIO(clean_png))
    assert post_png.format == "PNG"
    assert post_png.size == (60, 40)


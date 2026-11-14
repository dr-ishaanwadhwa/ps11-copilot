"""Tests for Salesman Collection Slip (Parchi) Ingestion, FIFO Invoice Allocation,
and Godown Cash Drawer Balancing (Milestone 2 / R3).
"""
import pandas as pd
import pytest

from copilot.gemini import ocr_collection_slip
from copilot.load import load_pack
from copilot.masking import sanitize_slip_image
from copilot.match.engine import Matcher, SUGGEST
from copilot.match.names import match_retailer_name
from copilot.vault import Collection, GallaEntry, VaultDB, VaultLockedError
from copilot.vault.db import allocate_collection_to_invoices
from copilot.vault.models import calculate_drawer_balance


def test_collection_model_initialization_and_aliases():
    """Verify Collection model initializes cleanly with standard and alias kwargs."""
    # Positional instantiation
    c1 = Collection(
        "SME-1",
        pd.Timestamp("2026-09-30"),
        "Laxmi Super Mart, Bibwewadi",
        15000.0,
        "Ramesh Kumar",
        "CASH",
        "SLIP-TEST-001",
        "INV-1001",
    )
    assert c1.business_id == "SME-1"
    assert c1.date == pd.Timestamp("2026-09-30")
    assert c1.shop == "Laxmi Super Mart, Bibwewadi"
    assert c1.shop_name == "Laxmi Super Mart, Bibwewadi"
    assert c1.amount == 15000.0
    assert c1.salesman == "Ramesh Kumar"
    assert c1.salesman_name == "Ramesh Kumar"
    assert c1.payment_mode == "CASH"
    assert c1.slip_id == "SLIP-TEST-001"
    assert c1.slip_no == "SLIP-TEST-001"
    assert c1.invoice_no == "INV-1001"
    assert c1.is_banked is False

    # Alias kwargs instantiation
    c2 = Collection(
        business_id="SME-1",
        date="2026-09-30",
        shop_name="Mahalaxmi Supermarket, Nigdi",
        amount=22500.5,
        salesman_name="Vijay Patil",
        payment_mode="upi",  # lower case normalized
        slip_no="SLIP-UPI-002",
        invoice_no="INV-1002",
    )
    assert c2.shop == "Mahalaxmi Supermarket, Nigdi"
    assert c2.shop_name == "Mahalaxmi Supermarket, Nigdi"
    assert c2.salesman == "Vijay Patil"
    assert c2.salesman_name == "Vijay Patil"
    assert c2.payment_mode == "UPI"
    assert c2.slip_id == "SLIP-UPI-002"
    assert c2.slip_no == "SLIP-UPI-002"

    # Property setters
    c2.shop_name = "Updated Shop Name"
    assert c2.shop == "Updated Shop Name"
    c2.salesman_name = "New Salesman"
    assert c2.salesman == "New Salesman"
    c2.slip_no = "SLIP-UPDATED-003"
    assert c2.slip_id == "SLIP-UPDATED-003"


def test_vault_record_collection_and_drawer_auto_increment():
    """Verify VaultDB.record_collection updates cash drawer cash_in for CASH slips."""
    vault = VaultDB(in_memory=True)
    vault.unlock("0000")

    date_t = pd.Timestamp("2026-09-30")

    # Initial galla entry
    g0 = GallaEntry(
        business_id="SME-1",
        date=date_t,
        opening_cash=20000.0,
        cash_in=5000.0,
        cash_out=1000.0,
        cash_banked=10000.0,
        counted_cash=14000.0,
        notes="Opening day float",
    )
    vault.record_galla(g0)

    # 1. CASH collection increments cash_in
    c_cash = Collection(
        business_id="SME-1",
        date=date_t,
        shop="Laxmi Super Mart, Bibwewadi",
        amount=12000.0,
        payment_mode="CASH",
        salesman="Ramesh Kumar",
    )
    slip_id = vault.record_collection(c_cash, update_drawer=True)
    assert slip_id.startswith("SLIP-")

    g1 = vault.get_latest_galla("SME-1")
    assert g1 is not None
    assert g1.cash_in == 17000.0  # 5000 + 12000

    # 2. UPI collection does NOT increment physical cash drawer
    c_upi = Collection(
        business_id="SME-1",
        date=date_t,
        shop="Gajanan Super Mart, Aundh",
        amount=8000.0,
        payment_mode="UPI",
        salesman="Suresh Shinde",
    )
    vault.record_collection(c_upi, update_drawer=True)
    g2 = vault.get_latest_galla("SME-1")
    assert g2.cash_in == 17000.0

    # 3. CHEQUE collection does NOT increment physical cash drawer
    c_chq = Collection(
        business_id="SME-1",
        date=date_t,
        shop="New Mini Mart, Hadapsar",
        amount=15000.0,
        payment_mode="CHEQUE",
        salesman="Vijay Patil",
    )
    vault.record_collection(c_chq, update_drawer=True)
    g3 = vault.get_latest_galla("SME-1")
    assert g3.cash_in == 17000.0

    # 4. update_drawer=False does NOT increment physical cash drawer
    c_cash_no_update = Collection(
        business_id="SME-1",
        date=date_t,
        shop="Shop Without Update",
        amount=3000.0,
        payment_mode="CASH",
    )
    vault.record_collection(c_cash_no_update, update_drawer=False)
    g4 = vault.get_latest_galla("SME-1")
    assert g4.cash_in == 17000.0


def test_vault_record_collection_auto_initializes_galla_when_none_exists():
    """Verify that if no GallaEntry exists for the date, one is auto-initialized with 0 opening cash."""
    vault = VaultDB(in_memory=True)
    vault.unlock("0000")

    new_date = pd.Timestamp("2026-10-05")

    # Record cash collection on a date with no prior GallaEntry
    c_cash = Collection(
        business_id="SME-1",
        date=new_date,
        shop="Fresh Market, Kothrud",
        amount=7500.0,
        payment_mode="CASH",
        salesman="Deepak",
    )
    vault.record_collection(c_cash, update_drawer=True)

    latest_g = vault.get_latest_galla("SME-1")
    assert latest_g is not None
    assert latest_g.date == new_date
    assert latest_g.opening_cash == 0.0
    assert latest_g.cash_in == 7500.0
    assert latest_g.cash_out == 0.0
    assert latest_g.cash_banked == 0.0
    assert latest_g.expected_cash == 7500.0
    assert latest_g.is_balanced is True

    # Record second cash collection on the same date: accumulates cash_in
    c_cash_2 = Collection(
        business_id="SME-1",
        date=new_date,
        shop="Super Market, Baner",
        amount=2500.0,
        payment_mode="CASH",
        salesman="Deepak",
    )
    vault.record_collection(c_cash_2, update_drawer=True)
    latest_g2 = vault.get_latest_galla("SME-1")
    assert latest_g2.cash_in == 10000.0


def test_record_collection_with_dictionary_input():
    """Verify record_collection supports passing a dictionary."""
    vault = VaultDB(in_memory=True)
    vault.unlock("0000")

    slip_dict = {
        "business_id": "SME-1",
        "date": "2026-09-30",
        "shop_name": "Laxmi Kirana",
        "amount": 4200.0,
        "payment_mode": "CASH",
        "salesman_name": "Suresh",
        "slip_no": "SLIP-DICT-01",
    }
    slip_id = vault.record_collection(slip_dict, update_drawer=True)
    assert slip_id == "SLIP-DICT-01"

    cols = vault.get_collections("SME-1")
    assert len(cols) == 1
    assert cols[0].shop == "Laxmi Kirana"
    assert cols[0].amount == 4200.0


def test_get_unbanked_collections_and_shop_queries():
    """Verify get_unbanked_collections, get_collections_for_shop, and mark_collection_banked."""
    vault = VaultDB(in_memory=True)
    vault.unlock("0000")

    date_t = pd.Timestamp("2026-09-30")

    c1 = Collection("SME-1", date_t, "Shop Alpha", 5000.0, "Salesman 1", slip_id="SLIP-A")
    c2 = Collection("SME-1", date_t, "Shop Beta", 7000.0, "Salesman 2", slip_id="SLIP-B")
    c3 = Collection("SME-1", date_t, "Shop Alpha", 3000.0, "Salesman 1", slip_id="SLIP-C")
    c_other_biz = Collection("SME-2", date_t, "Clinic Patient", 2000.0, slip_id="SLIP-D")

    vault.record_collection(c1)
    vault.record_collection(c2)
    vault.record_collection(c3)
    vault.record_collection(c_other_biz)

    # Initial unbanked list
    unbanked_sme1 = vault.get_unbanked_collections("SME-1")
    assert len(unbanked_sme1) == 3

    # Mark c1 as banked
    vault.mark_collection_banked("SLIP-A", bank_txn_id="TXN-BANK-101")
    assert c1.is_banked is True
    assert c1.bank_txn_id == "TXN-BANK-101"

    # Unbanked should now exclude c1
    unbanked_after = vault.get_unbanked_collections("SME-1")
    assert len(unbanked_after) == 2
    assert {c.slip_id for c in unbanked_after} == {"SLIP-B", "SLIP-C"}

    # Query collections for a specific shop
    alpha_cols = vault.get_collections_for_shop("SME-1", "Shop Alpha")
    assert len(alpha_cols) == 2
    assert {c.slip_id for c in alpha_cols} == {"SLIP-A", "SLIP-C"}

    # Case-insensitive shop query
    alpha_cols_ci = vault.get_collections_for_shop("SME-1", "shop alpha ")
    assert len(alpha_cols_ci) == 2

    # Locked vault raises VaultLockedError
    vault.lock()
    with pytest.raises(VaultLockedError):
        vault.get_unbanked_collections("SME-1")
    with pytest.raises(VaultLockedError):
        vault.get_collections_for_shop("SME-1", "Shop Alpha")


def test_fifo_invoice_allocation_engine():
    """Verify FIFO invoice allocation applies collection amounts against oldest bills first."""
    open_invs = pd.DataFrame([
        {
            "invoice_no": "KD/24-25/001",
            "customer_name": "Laxmi Super Mart",
            "invoice_date": pd.Timestamp("2026-08-01"),
            "invoice_total": 10000.0,
            "outstanding": 10000.0,
        },
        {
            "invoice_no": "KD/24-25/002",
            "customer_name": "Laxmi Super Mart",
            "invoice_date": pd.Timestamp("2026-08-15"),
            "invoice_total": 8000.0,
            "outstanding": 8000.0,
        },
        {
            "invoice_no": "KD/24-25/003",
            "customer_name": "Laxmi Super Mart",
            "invoice_date": pd.Timestamp("2026-09-01"),
            "invoice_total": 15000.0,
            "outstanding": 15000.0,
        },
    ])

    # Case 1: Collection of ₹14,000 clears invoice 001 fully (₹10,000) and invoice 002 partially (₹4,000)
    col = Collection(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        shop="Laxmi Super Mart",
        amount=14000.0,
        slip_id="SLIP-ALLOC-01",
    )

    allocs = allocate_collection_to_invoices(col, open_invs, mode="FIFO")
    assert len(allocs) == 2

    # First bill: fully paid
    assert allocs[0]["invoice_no"] == "KD/24-25/001"
    assert allocs[0]["previous_balance"] == 10000.0
    assert allocs[0]["allocated_amount"] == 10000.0
    assert allocs[0]["remaining_balance"] == 0.0
    assert allocs[0]["status"] == "PAID"
    assert allocs[0]["slip_id"] == "SLIP-ALLOC-01"

    # Second bill: partially paid
    assert allocs[1]["invoice_no"] == "KD/24-25/002"
    assert allocs[1]["previous_balance"] == 8000.0
    assert allocs[1]["allocated_amount"] == 4000.0
    assert allocs[1]["remaining_balance"] == 4000.0
    assert allocs[1]["status"] == "PARTIALLY_PAID"

    # Total allocated equals collection amount
    assert sum(a["allocated_amount"] for a in allocs) == 14000.0


def test_explicit_invoice_allocation_engine():
    """Verify explicit invoice allocation prioritizes targeted invoice_no."""
    open_invs = pd.DataFrame([
        {
            "invoice_no": "KD/24-25/001",
            "customer_name": "Laxmi Super Mart",
            "invoice_date": pd.Timestamp("2026-08-01"),
            "invoice_total": 10000.0,
            "outstanding": 10000.0,
        },
        {
            "invoice_no": "KD/24-25/002",
            "customer_name": "Laxmi Super Mart",
            "invoice_date": pd.Timestamp("2026-08-15"),
            "invoice_total": 8000.0,
            "outstanding": 8000.0,
        },
    ])

    # Target the newer invoice (002) specifically
    col = Collection(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        shop="Laxmi Super Mart",
        amount=8000.0,
        invoice_no="KD/24-25/002",
        slip_id="SLIP-TARGET-02",
    )

    # In EXPLICIT mode, only the target invoice is paid
    allocs = allocate_collection_to_invoices(col, open_invs, mode="EXPLICIT")
    assert len(allocs) == 1
    assert allocs[0]["invoice_no"] == "KD/24-25/002"
    assert allocs[0]["allocated_amount"] == 8000.0
    assert allocs[0]["remaining_balance"] == 0.0
    assert allocs[0]["status"] == "PAID"


def test_godown_drawer_balancing_calculation():
    """Verify 5-variable cash equation: expected_cash = opening + in - out - banked, drift tolerance ±50."""
    # Balanced exactly
    bal1 = calculate_drawer_balance(
        opening_cash=50000.0,
        cash_in=25000.0,
        cash_out=5000.0,
        cash_banked=30000.0,
        counted_cash=40000.0,
    )
    assert bal1["expected_cash"] == 40000.0
    assert bal1["drift"] == 0.0
    assert bal1["is_balanced"] is True
    assert bal1["status_label"] == "Balanced"

    # Within ₹50 tolerance: +₹20 drift is still Balanced
    bal2 = calculate_drawer_balance(
        opening_cash=50000.0,
        cash_in=25000.0,
        cash_out=5000.0,
        cash_banked=30000.0,
        counted_cash=40020.0,
    )
    assert bal2["drift"] == 20.0
    assert bal2["is_balanced"] is True
    assert bal2["status_label"] == "Balanced"

    # Unbalanced: -₹150 drift is flagged
    bal3 = calculate_drawer_balance(
        opening_cash=50000.0,
        cash_in=25000.0,
        cash_out=5000.0,
        cash_banked=30000.0,
        counted_cash=39850.0,
    )
    assert bal3["drift"] == -150.0
    assert bal3["is_balanced"] is False
    assert bal3["status_label"] == "Drift to check"

    # GallaEntry dataclass properties match
    entry = GallaEntry(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        opening_cash=50000.0,
        cash_in=25000.0,
        cash_out=5000.0,
        cash_banked=30000.0,
        counted_cash=39850.0,
    )
    assert entry.expected_cash == 40000.0
    assert entry.drift == -150.0
    assert entry.is_balanced is False
    assert entry.status_label == "Drift to check"


def test_cash_deposit_matching_integration_with_explicit_slips():
    """Verify Matcher resolves distributor cash deposits when collection slips link open invoices."""
    pack = load_pack()
    vault = VaultDB(in_memory=True)
    vault.unlock("0000")

    mt = Matcher(pack, vault=vault)

    # Pick 2 open invoices for distinct shops
    target_docs = []
    for party, docs in mt.docs["SME-1"].items():
        for d in docs:
            if d.remaining > 500:
                target_docs.append(d)
                break
        if len(target_docs) == 2:
            break

    assert len(target_docs) == 2
    dep_amt = sum(d.remaining for d in target_docs)
    dep_date = max(d.date for d in target_docs) + pd.Timedelta(days=3)

    # Record collection slips in vault
    for d in target_docs:
        col = Collection(
            business_id="SME-1",
            date=dep_date - pd.Timedelta(days=1),
            shop=d.party,
            amount=d.remaining,
            salesman="Ramesh",
            invoice_no=d.id,
            payment_mode="CASH",
        )
        vault.record_collection(col)

    # Synthetic bank cash deposit transaction
    from types import SimpleNamespace
    row = SimpleNamespace(
        txn_id="TXN-DEPOSIT-INTEG-001",
        business_id="SME-1",
        channel="CASH",
        amount=dep_amt,
        txn_date=dep_date,
        narration="CASH DEPOSIT BY SELF - CDM HADAPSAR",
        seq=1,
    )

    m = mt.match(row)
    assert m is not None
    assert m.tier == SUGGEST
    assert m.rule == "CASH_DEPOSIT"
    matched_ids = {doc_id for doc_id, _ in m.docs}
    assert matched_ids == {d.id for d in target_docs}

    # Verify collection slips are marked as banked
    unbanked = vault.get_unbanked_collections("SME-1")
    assert len(unbanked) == 0


def test_match_retailer_name_with_sme1_verified_parties():
    """Verify RapidFuzz matching against all 115 verified SME-1 parties."""
    pack = load_pack()
    sme1_df = pack.parties[pack.parties["business_id"] == "SME-1"]
    parties = sorted(sme1_df["party_name"].dropna().unique().tolist())
    assert len(parties) == 115, f"Expected 115 parties for SME-1, got {len(parties)}"

    # 1. Partial shop name omitting locality
    match_laxmi, score_laxmi = match_retailer_name("Laxmi Kirana", parties)
    assert match_laxmi == "Laxmi Kirana Stores, Sinhagad Road"
    assert score_laxmi >= 0.80

    # 2. Store with locality in query
    match_swami, score_swami = match_retailer_name("Swami Provision Baner", parties)
    assert match_swami == "Swami Provision Stores, Baner"
    assert score_swami >= 0.85

    # 3. Another partial store
    match_gajanan, score_gajanan = match_retailer_name("Gajanan Super Mart", parties)
    assert match_gajanan == "Gajanan Super Mart, Aundh"
    assert score_gajanan >= 0.80

    # 4. Unknown store query below threshold returns query and 0.0 score
    unknown_q = "Totally Unknown Mart 999"
    match_unknown, score_unknown = match_retailer_name(unknown_q, parties)
    assert match_unknown == unknown_q
    assert score_unknown == 0.0

    # 5. Empty inputs
    assert match_retailer_name("", parties) == ("", 0.0)
    assert match_retailer_name("Laxmi", []) == ("Laxmi", 0.0)

    # 6. Generic single stop words do NOT return 100% false-positive match
    for generic_word in ["Kirana", "Provision", "General Stores", "Mart"]:
        m_res, m_conf = match_retailer_name(generic_word, parties)
        assert m_conf < 0.65, f"Generic word '{generic_word}' produced unacceptable high confidence: {m_conf}"


def test_parchi_photo_sanitization_and_ocr_flow():
    """Verify end-to-end parchi ingestion: photo sanitization -> OCR extraction -> RapidFuzz matching -> VaultDB persistence."""
    import io
    from unittest.mock import MagicMock, patch
    from PIL import Image

    # 1. Simulate physical camera photo with EXIF metadata
    img = Image.new("RGB", (100, 100), color="white")
    exif = Image.Exif()
    exif[271] = "Apple"
    exif[272] = "iPhone 15 Pro"
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw_photo_bytes = buf.getvalue()

    # 2. Local PII sanitization strips camera metadata
    sanitized_bytes = sanitize_slip_image(raw_photo_bytes)
    check_img = Image.open(io.BytesIO(sanitized_bytes))
    assert len(dict(check_img.getexif())) == 0

    # 3. Gemini Vision OCR extraction
    import json
    fake_ocr = {
        "retailer_name": "Laxmi Kirana",
        "shop": "Laxmi Kirana",
        "amount": 18500.0,
        "payment_mode": "Cash",
        "salesman": "Ramesh Kumar",
        "date": "2026-09-30",
        "slip_no": "SLIP-ROUTE-42",
        "confidence": 0.95,
        "notes": "Payment for August invoices",
    }
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": json.dumps(fake_ocr)}]
                }
            }
        ]
    }
    with patch("copilot.gemini.requests.post", return_value=fake_response):
        with patch("copilot.gemini._get_api_key", return_value="fake-key"):
            ocr_res = ocr_collection_slip(sanitized_bytes)

    # 4. Match retailer name against verified parties
    pack = load_pack()
    parties = sorted(pack.parties[pack.parties["business_id"] == "SME-1"]["party_name"].dropna().unique().tolist())
    matched_party, match_conf = match_retailer_name(ocr_res["retailer_name"], parties)
    assert matched_party == "Laxmi Kirana Stores, Sinhagad Road"
    assert match_conf >= 0.80

    # 5. Commit to volatile RAM VaultDB with 1-click confirmation
    vault = VaultDB(in_memory=True)
    vault.unlock("0000")
    g0 = GallaEntry(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        opening_cash=10000.0,
        cash_in=0.0,
        cash_out=0.0,
        cash_banked=0.0,
        counted_cash=10000.0,
    )
    vault.record_galla(g0)

    coll = Collection(
        business_id="SME-1",
        date=pd.Timestamp(ocr_res["date"]),
        shop=matched_party,
        amount=float(ocr_res["amount"]),
        salesman=ocr_res["salesman"],
        payment_mode=ocr_res["payment_mode"].upper(),
        slip_id=ocr_res["slip_no"],
        notes=ocr_res["notes"],
    )
    recorded_id = vault.record_collection(coll, update_drawer=True)
    assert recorded_id == "SLIP-ROUTE-42"

    # Verify CASH collection increments cash drawer cash_in
    g_after = vault.get_latest_galla("SME-1")
    assert g_after.cash_in == 18500.0
    assert g_after.expected_cash == 28500.0


def test_parchi_upi_and_cheque_isolation():
    """Verify that non-cash collection slips (UPI/Cheque) do not inflate cash drawer float."""
    vault = VaultDB(in_memory=True)
    vault.unlock("0000")
    g0 = GallaEntry(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        opening_cash=15000.0,
        cash_in=2000.0,
        cash_out=500.0,
        cash_banked=0.0,
        counted_cash=16500.0,
    )
    vault.record_galla(g0)

    # Record UPI slip
    c_upi = Collection(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        shop="Swami Provision Stores, Baner",
        amount=12000.0,
        payment_mode="UPI",
        salesman="Vijay Patil",
        slip_id="SLIP-UPI-01",
    )
    vault.record_collection(c_upi, update_drawer=True)
    assert vault.get_latest_galla("SME-1").cash_in == 2000.0

    # Record Cheque slip
    c_chq = Collection(
        business_id="SME-1",
        date=pd.Timestamp("2026-09-30"),
        shop="Gajanan Super Mart, Aundh",
        amount=30000.0,
        payment_mode="CHEQUE",
        salesman="Suresh Shinde",
        slip_id="SLIP-CHQ-01",
    )
    vault.record_collection(c_chq, update_drawer=True)
    assert vault.get_latest_galla("SME-1").cash_in == 2000.0

    # Verify all slips are stored in vault collections
    cols = vault.get_collections("SME-1")
    assert len(cols) == 2
    assert {c.slip_id for c in cols} == {"SLIP-UPI-01", "SLIP-CHQ-01"}


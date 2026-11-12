"""Tests for bank statement parser and Tally XML ingestion."""
import pandas as pd
import pytest

from copilot.ingest import parse_bank_statement, parse_tally_xml


def test_parse_bank_statement_csv():
    csv_data = (
        "Date,Narration,Withdrawal,Deposit,Balance\n"
        "01/10/2026,UPI-OM SUPERMARKET-PAY,0,15000,115000\n"
        "02/10/2026,SALARY NEFT DISBURSEMENT,50000,0,65000\n"
        "03/10/2026,CASH DEPOSIT GALLA,0,20000,85000\n"
    ).encode("utf-8")

    res = parse_bank_statement(csv_data, "hdfc_statement.csv")
    assert res["rows_read"] == 3
    assert res["balance_ties"] is True
    assert len(res["breaks"]) == 0
    assert res["summary"]["total_credits"] == 35000.0
    assert res["summary"]["total_debits"] == 50000.0
    assert res["summary"]["closing_balance"] == 85000.0


def test_parse_bank_statement_broken_balance():
    csv_data = (
        "Date,Narration,Withdrawal,Deposit,Balance\n"
        "01/10/2026,OPENING BALANCE,0,10000,10000\n"
        "02/10/2026,MISSING TXN LEAP,0,5000,50000\n"  # 10000 + 5000 != 50000
    ).encode("utf-8")

    res = parse_bank_statement(csv_data, "icici_statement.csv")
    assert res["rows_read"] == 2
    assert res["balance_ties"] is False
    assert 1 in res["breaks"]


def test_parse_tally_xml():
    xml_data = """
    <ENVELOPE>
      <BODY>
        <DATA>
          <TALLYMESSAGE>
            <LEDGER NAME="Laxmi Super Mart">
              <BILLALLOCATIONS.LIST>
                <NAME>INV-2026-089</NAME>
                <BILLTYPE>New Ref</BILLTYPE>
                <AMOUNT>45000.00</AMOUNT>
              </BILLALLOCATIONS.LIST>
              <BILLALLOCATIONS.LIST>
                <NAME>INV-2026-092</NAME>
                <BILLTYPE>New Ref</BILLTYPE>
                <AMOUNT>28500.00</AMOUNT>
              </BILLALLOCATIONS.LIST>
            </LEDGER>
          </TALLYMESSAGE>
        </DATA>
      </BODY>
    </ENVELOPE>
    """
    df = parse_tally_xml(xml_data)
    assert len(df) == 2
    assert df.iloc[0]["party_name"] == "Laxmi Super Mart"
    assert df.iloc[0]["bill_name"] == "INV-2026-089"
    assert df.iloc[0]["amount"] == 45000.0
    assert df.iloc[1]["amount"] == 28500.0

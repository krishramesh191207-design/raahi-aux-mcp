"""Tests for Raahi Auxiliary MCP tools."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from src.store import reset_demo, DEMO_APPLICANT_ID
from src.tools import (
    verify_pan,
    create_digilocker_consent,
    fetch_digilocker_doc,
    esign_document,
    collect_payment,
    get_payment_status,
    issue_travel_insurance,
    request_bank_letter,
    update_bank_letter_status_tool,
    check_serviceability_mock,
    schedule_document_pickup_mock,
    track_shipment_mock,
    standardise_address_mock,
    estimate_route_mock,
    get_demo_case,
    reset_demo_case,
    get_audit_log_tool,
)


@pytest.fixture(autouse=True)
def fresh_demo():
    reset_demo()
    yield
    reset_demo()


# ---------------------------------------------------------------------------
# verify_pan
# ---------------------------------------------------------------------------

def test_verify_pan_valid():
    r = verify_pan("ABCDE1234F")
    assert r["success"] is True
    assert r["mode"] == "mock"
    assert r["valid"] is True
    assert "ABCDE1234F" not in str(r)  # raw PAN never in response
    assert r["masked_pan"] == "ABCD****F"


def test_verify_pan_name_match():
    r = verify_pan("ABCDE1234F", expected_name="Ananya Sharma")
    assert r["name_match"] is True

    r2 = verify_pan("ABCDE1234F", expected_name="Wrong Name")
    assert r2["name_match"] is False


def test_verify_pan_invalid_format():
    r = verify_pan("INVALID123")
    assert r["success"] is False
    assert r["error_code"] == "INVALID_PAN_FORMAT"


def test_verify_pan_simulate_failure():
    r = verify_pan("ABCDE1234F", simulate_failure=True)
    assert r["success"] is False
    assert r["error_code"] == "NSDL_UNAVAILABLE"


# ---------------------------------------------------------------------------
# DigiLocker consent + fetch
# ---------------------------------------------------------------------------

def test_create_consent_returns_url():
    r = create_digilocker_consent(DEMO_APPLICANT_ID, "+919999999999", "visa", ["aadhaar"])
    assert r["success"] is True
    assert "consent_id" in r
    assert "raahi-demo.example" in r["consent_url"]
    assert "aadhaar" in r["requested_documents"]


def test_create_consent_unsupported_doc():
    r = create_digilocker_consent(DEMO_APPLICANT_ID, "+91999", "visa", ["bank_statement"])
    assert r["success"] is False
    assert r["error_code"] == "UNSUPPORTED_DOC_TYPE"


def test_fetch_doc_requires_consent():
    r = fetch_digilocker_doc("", "aadhaar", DEMO_APPLICANT_ID)
    assert r["success"] is False
    assert r["error_code"] == "CONSENT_REQUIRED"


def test_fetch_doc_consent_not_found():
    r = fetch_digilocker_doc("NONEXISTENT", "aadhaar", DEMO_APPLICANT_ID)
    assert r["success"] is False
    assert r["error_code"] == "CONSENT_NOT_FOUND"


def test_fetch_doc_ok():
    c = create_digilocker_consent(DEMO_APPLICANT_ID, "+91999", "visa", ["aadhaar", "passport"])
    r = fetch_digilocker_doc(c["consent_id"], "aadhaar", DEMO_APPLICANT_ID)
    assert r["success"] is True
    assert r["document_type"] == "aadhaar"
    assert r["document_status"] == "verified"


def test_fetch_doc_not_in_consent():
    c = create_digilocker_consent(DEMO_APPLICANT_ID, "+91999", "visa", ["aadhaar"])
    r = fetch_digilocker_doc(c["consent_id"], "passport", DEMO_APPLICANT_ID)
    assert r["success"] is False
    assert r["error_code"] == "DOC_NOT_IN_CONSENT"


def test_fetch_doc_simulate_unavailable():
    c = create_digilocker_consent(DEMO_APPLICANT_ID, "+91999", "visa", ["aadhaar"])
    r = fetch_digilocker_doc(c["consent_id"], "aadhaar", DEMO_APPLICANT_ID, simulate_unavailable=True)
    assert r["success"] is False
    assert r["error_code"] == "DOCUMENT_UNAVAILABLE"


# ---------------------------------------------------------------------------
# eSign
# ---------------------------------------------------------------------------

def test_esign_blocked_without_review():
    r = esign_document("hash1", "+919999999999", DEMO_APPLICANT_ID, applicant_has_seen_document=False)
    assert r["success"] is False
    assert r["error_code"] == "DOCUMENT_NOT_REVIEWED"


def test_esign_ok():
    r = esign_document("hash1", "+919999999999", DEMO_APPLICANT_ID, applicant_has_seen_document=True)
    assert r["success"] is True
    assert r["status"] == "SIGNED"
    assert "+919999999999" not in str(r)  # phone masked


def test_esign_otp_failure():
    r = esign_document("hash1", "+919999999999", DEMO_APPLICANT_ID, True, simulate_otp_failure=True, failure_mode="OTP_TIMEOUT")
    assert r["success"] is False
    assert r["error_code"] == "OTP_TIMEOUT"


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

def test_collect_payment_ok():
    r = collect_payment(4999, DEMO_APPLICANT_ID, "Visa fee")
    assert r["success"] is True
    assert r["status"] == "PENDING"
    assert r["amount"] == 4999
    assert "transaction_id" in r


def test_collect_payment_zero():
    r = collect_payment(0, DEMO_APPLICANT_ID, "zero")
    assert r["success"] is False
    assert r["error_code"] == "INVALID_AMOUNT"


def test_collect_payment_decline():
    r = collect_payment(999, DEMO_APPLICANT_ID, "test", simulate_decline=True)
    assert r["status"] == "DECLINED"


def test_get_payment_status_force():
    p = collect_payment(999, DEMO_APPLICANT_ID, "test")
    r = get_payment_status(p["transaction_id"], force_status="SUCCESS")
    assert r["status"] == "SUCCESS"


def test_get_payment_status_invalid_force():
    p = collect_payment(999, DEMO_APPLICANT_ID, "test")
    r = get_payment_status(p["transaction_id"], force_status="MAGIC")
    assert r["success"] is False


def test_get_payment_not_found():
    r = get_payment_status("TXNBAD")
    assert r["success"] is False
    assert r["error_code"] == "TRANSACTION_NOT_FOUND"


# ---------------------------------------------------------------------------
# Insurance
# ---------------------------------------------------------------------------

def test_insurance_requires_payment():
    r = issue_travel_insurance(
        DEMO_APPLICANT_ID, "Ananya", "P1234567", "France",
        "2026-11-10", "2026-11-20", 500000, 3999, "NONEXISTENT"
    )
    assert r["success"] is False
    assert r["error_code"] == "PAYMENT_NOT_FOUND"


def test_insurance_ok():
    p = collect_payment(3999, DEMO_APPLICANT_ID, "Insurance premium")
    get_payment_status(p["transaction_id"], force_status="SUCCESS")
    r = issue_travel_insurance(
        DEMO_APPLICANT_ID, "Ananya", "P1234567", "France",
        "2026-11-10", "2026-11-20", 500000, 3999, p["transaction_id"]
    )
    assert r["success"] is True
    assert "policy_id" in r
    assert "P1234567" not in str(r)  # passport masked
    assert r["certificate_type"] == "DEMO / MOCK INSURANCE CERTIFICATE"


def test_insurance_bad_dates():
    p = collect_payment(3999, DEMO_APPLICANT_ID, "Insurance premium")
    r = issue_travel_insurance(
        DEMO_APPLICANT_ID, "Ananya", "P1234567", "France",
        "2026-11-20", "2026-11-10", 500000, 3999, p["transaction_id"]
    )
    assert r["success"] is False
    assert r["error_code"] == "INVALID_DATES"


# ---------------------------------------------------------------------------
# Bank letter
# ---------------------------------------------------------------------------

def test_request_bank_letter():
    r = request_bank_letter(DEMO_APPLICANT_ID, "HDFC", "123456789", "Visa", "2026-10-20", "courier")
    assert r["success"] is True
    assert r["status"] == "REQUESTED"
    assert "123456789" not in str(r)  # account masked


def test_update_bank_letter_valid_transition():
    bl = request_bank_letter(DEMO_APPLICANT_ID, "HDFC", "123456789", "Visa", "2026-10-20", "courier")
    r = update_bank_letter_status_tool(bl["request_id"], "BANK_CONTACTED")
    assert r["success"] is True
    assert r["status"] == "BANK_CONTACTED"


def test_update_bank_letter_invalid_transition():
    bl = request_bank_letter(DEMO_APPLICANT_ID, "HDFC", "123456789", "Visa", "2026-10-20", "courier")
    r = update_bank_letter_status_tool(bl["request_id"], "COMPLETED")
    assert r["success"] is False
    assert r["error_code"] == "INVALID_TRANSITION"


def test_update_bank_letter_not_found():
    r = update_bank_letter_status_tool("NONEXISTENT", "BANK_CONTACTED")
    assert r["success"] is False
    assert r["error_code"] == "REQUEST_NOT_FOUND"


# ---------------------------------------------------------------------------
# Logistics
# ---------------------------------------------------------------------------

def test_check_serviceability():
    r = check_serviceability_mock("110001", "400001")
    assert r["success"] is True
    assert "serviceable" in r


def test_schedule_and_track_shipment():
    s = schedule_document_pickup_mock("A-1 Delhi", "VFS Delhi", "10-14", ["passport"], DEMO_APPLICANT_ID)
    assert s["success"] is True
    awb = s["awb"]

    t = track_shipment_mock(awb)
    assert t["success"] is True
    assert t["status"] in ("PICKUP_SCHEDULED", "CREATED")


def test_track_unknown_awb():
    r = track_shipment_mock("FAKE-AWB-XYZ")
    assert r["success"] is False
    assert r["error_code"] == "AWB_NOT_FOUND"


def test_standardise_address_resolved():
    r = standardise_address_mock("A-101, Connaught Place, New Delhi, 110001")
    assert r["success"] is True
    assert r["resolved"] is True


def test_standardise_address_ambiguous():
    r = standardise_address_mock("somewhere")
    assert r["resolved"] is False


def test_estimate_route():
    r = estimate_route_mock("Delhi", "Mumbai")
    assert r["success"] is True
    assert r["distance_km"] > 0
    assert r["eta_minutes"] > 0


# ---------------------------------------------------------------------------
# Demo case / reset / audit
# ---------------------------------------------------------------------------

def test_get_demo_case():
    r = get_demo_case()
    assert r["success"] is True
    assert r["applicant"]["name"] == "Ananya Sharma"


def test_reset_demo_case():
    collect_payment(999, DEMO_APPLICANT_ID, "test")
    r = reset_demo_case()
    assert r["success"] is True
    after = get_demo_case()
    assert len(after["payments"]) == 0


def test_audit_log_captures_events():
    verify_pan("ABCDE1234F")
    collect_payment(999, DEMO_APPLICANT_ID, "x")
    r = get_audit_log_tool()
    assert r["total_events"] >= 2
    # Raw PAN (10-char format) must never appear in audit log
    for evt in r["events"]:
        assert "ABCDE1234F" not in str(evt), "Raw PAN must not appear in audit log"


# ---------------------------------------------------------------------------
# Failure mode: malformed transcript (Gnani STT)
# ---------------------------------------------------------------------------

def test_gnani_transcribe_malformed():
    from src import mock_connectors as MC
    r = MC.gnani_transcribe_speech("dummy_audio", simulate_malformed=True)
    assert r["success"] is False
    assert r["error_code"] == "MALFORMED_TRANSCRIPT"
    assert "partial_transcript" in r
    assert r["confidence"] < 0.5


# ---------------------------------------------------------------------------
# Failure mode: call timeout (Gnani outbound call)
# ---------------------------------------------------------------------------

def test_gnani_call_timeout():
    from src import mock_connectors as MC
    r = MC.gnani_call_bank_rm("bot1", "+919999999999", "+91", "Ananya", simulate_timeout=True)
    assert r["success"] is False
    assert r["error_code"] == "CALL_TIMEOUT"
    assert "retry_after_seconds" in r
    assert "next_available_slot" not in r  # timeout doesn't suggest address change


# ---------------------------------------------------------------------------
# Failure mode: low balance (Setu AA)
# ---------------------------------------------------------------------------

def test_aa_fetch_bank_data_low_balance():
    from src import mock_connectors as MC
    # First create a consent
    consent = MC.aa_request_consent("+919999999999", "RAAHI-DEMO-001", "visa_funds_proof")
    cid = consent["consent_id"]
    r = MC.aa_fetch_bank_data(cid, simulate_low_balance=True)
    assert r["success"] is True
    assert r["low_balance_flag"] is True
    assert r["accounts"][0]["balance"] < 50000  # below consulate minimum


# ---------------------------------------------------------------------------
# Failure mode: no rider available (Delhivery pickup)
# ---------------------------------------------------------------------------

def test_delhivery_no_rider_available():
    from src import mock_connectors as MC
    r = MC.delhivery_schedule_pickup(
        pickup_address="123 MG Road, Bengaluru",
        drop_address="VFS Global, Bengaluru",
        pickup_pincode="560001",
        drop_pincode="560025",
        time_window="14:00–18:00",
        documents=["passport", "bank_statement"],
        simulate_no_rider=True,
    )
    assert r["success"] is False
    assert r["error_code"] == "NO_RIDER_AVAILABLE"
    assert "next_available_slot" in r
    assert r["pickup_pincode"] == "560001"  # pincode preserved, not changed


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

def test_health_endpoint():
    from starlette.testclient import TestClient
    import server
    client = TestClient(server.app)
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["mode"] == "demo"
    assert body["service"] == "raahi-auxiliary-mcp"

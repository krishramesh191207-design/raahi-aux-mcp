"""
Tool implementations for the Raahi Auxiliary MCP.

All tools are MOCK / DEMO ONLY. No external services are called.
Every response includes mode="mock" and an explicit provider label.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any

from src.store import (
    DEMO_APPLICANT_ID,
    DEMO_PAN_REGISTRY,
    SUPPORTED_DOC_TYPES,
    VALID_PAYMENT_STATES,
    BANK_LETTER_TRANSITIONS,
    SHIPMENT_STATES,
    audit,
    create_consent,
    get_consent,
    create_payment,
    get_payment,
    set_payment_status,
    create_esign,
    create_policy,
    create_bank_letter_request,
    get_bank_letter_request,
    update_bank_letter_status,
    create_shipment,
    get_shipment,
    get_audit_log,
    reset_demo,
    mask_pan,
    mask_passport,
    mask_phone,
    new_id,
    now_iso,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _ok(provider: str, applicant_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
    return {"success": True, "mode": "mock", "provider": provider, **kwargs}


def _fail(provider: str, error_code: str, message: str, applicant_id: str | None = None, **kwargs: Any) -> dict[str, Any]:
    return {"success": False, "mode": "mock", "provider": provider, "error_code": error_code, "message": message, **kwargs}


# ---------------------------------------------------------------------------
# A. verify_pan
# ---------------------------------------------------------------------------

def verify_pan(
    pan: str,
    expected_name: str | None = None,
    simulate_failure: bool = False,
) -> dict[str, Any]:
    provider = "pine_labs_identity_mock"
    pan = pan.strip().upper()

    if simulate_failure:
        result = _fail(provider, "NSDL_UNAVAILABLE", "PAN verification service temporarily unavailable")
        audit("verify_pan", "mock", provider, None, "FAILED", "NSDL_UNAVAILABLE")
        return result

    if not _PAN_RE.match(pan):
        result = _fail(provider, "INVALID_PAN_FORMAT", f"PAN does not match expected format. masked: {mask_pan(pan)}")
        audit("verify_pan", "mock", provider, None, "FAILED", "INVALID_PAN_FORMAT")
        return result

    entry = DEMO_PAN_REGISTRY.get(pan)
    if entry is None:
        entry = {"name": "Unknown Demo Holder", "valid": True}

    name_match: bool | None = None
    if expected_name and entry.get("name"):
        name_match = expected_name.strip().lower() == entry["name"].strip().lower()

    result = _ok(
        provider,
        valid=entry["valid"],
        name_match=name_match,
        registered_name=entry.get("name"),
        masked_pan=mask_pan(pan),
        message="DEMO: PAN validated against mock registry. Not real NSDL verification.",
    )
    audit("verify_pan", "mock", provider, None, "OK")
    return result


# ---------------------------------------------------------------------------
# B. fetch_digilocker_doc
# ---------------------------------------------------------------------------

def fetch_digilocker_doc(
    consent_id: str,
    document_type: str,
    applicant_id: str,
    simulate_unavailable: bool = False,
) -> dict[str, Any]:
    provider = "digilocker_mock"

    if not consent_id:
        result = _fail(provider, "CONSENT_REQUIRED", "consent_id must be supplied. Never fetch a document without consent.")
        audit("fetch_digilocker_doc", "mock", provider, applicant_id, "FAILED", "CONSENT_REQUIRED")
        return result

    consent = get_consent(consent_id)
    if consent is None:
        result = _fail(provider, "CONSENT_NOT_FOUND", "No consent record found for this consent_id.")
        audit("fetch_digilocker_doc", "mock", provider, applicant_id, "FAILED", "CONSENT_NOT_FOUND")
        return result

    doc_type = document_type.lower().strip()
    if doc_type not in SUPPORTED_DOC_TYPES:
        result = _fail(
            provider,
            "UNSUPPORTED_DOC_TYPE",
            f"document_type '{doc_type}' not in supported list: {sorted(SUPPORTED_DOC_TYPES)}",
        )
        audit("fetch_digilocker_doc", "mock", provider, applicant_id, "FAILED", "UNSUPPORTED_DOC_TYPE")
        return result

    if doc_type not in (consent.get("requested_documents") or []):
        result = _fail(
            provider,
            "DOC_NOT_IN_CONSENT",
            f"Document type '{doc_type}' was not included in the original consent request.",
        )
        audit("fetch_digilocker_doc", "mock", provider, applicant_id, "FAILED", "DOC_NOT_IN_CONSENT")
        return result

    if simulate_unavailable:
        result = _fail(provider, "DOCUMENT_UNAVAILABLE", "Requested document not available in DigiLocker (mock simulation).")
        audit("fetch_digilocker_doc", "mock", provider, applicant_id, "FAILED", "DOCUMENT_UNAVAILABLE")
        return result

    doc_id = new_id("DL-MOCK-")
    result = _ok(
        provider,
        applicant_id=applicant_id,
        consent_id=consent_id,
        document_type=doc_type,
        document_id=doc_id,
        document_status="verified",
        document_url=f"https://raahi-demo.example/digilocker/{doc_id}",
        message="DEMO/MOCK: Mock DigiLocker document retrieved under supplied consent. Not a real government document.",
    )
    audit("fetch_digilocker_doc", "mock", provider, applicant_id, "OK")
    return result


# ---------------------------------------------------------------------------
# C. create_digilocker_consent
# ---------------------------------------------------------------------------

def create_digilocker_consent(
    applicant_id: str,
    mobile: str,
    purpose: str,
    requested_documents: list[str],
) -> dict[str, Any]:
    provider = "digilocker_mock"

    unsupported = [d for d in requested_documents if d.lower() not in SUPPORTED_DOC_TYPES]
    if unsupported:
        result = _fail(
            provider,
            "UNSUPPORTED_DOC_TYPE",
            f"Unsupported document types: {unsupported}. Supported: {sorted(SUPPORTED_DOC_TYPES)}",
        )
        audit("create_digilocker_consent", "mock", provider, applicant_id, "FAILED", "UNSUPPORTED_DOC_TYPE")
        return result

    docs = [d.lower() for d in requested_documents]
    rec = create_consent(applicant_id, mobile, purpose, docs)

    result = _ok(
        provider,
        applicant_id=applicant_id,
        consent_id=rec["consent_id"],
        status=rec["status"],
        requested_documents=docs,
        consent_url=f"https://raahi-demo.example/consent/{rec['consent_id']}",
        message="DEMO/MOCK: Consent record created. Consent URL is not a real DigiLocker URL.",
    )
    audit("create_digilocker_consent", "mock", provider, applicant_id, "OK")
    return result


# ---------------------------------------------------------------------------
# D. esign_document
# ---------------------------------------------------------------------------

def esign_document(
    document_hash: str,
    aadhaar_linked_mobile: str,
    applicant_id: str,
    applicant_has_seen_document: bool,
    simulate_otp_failure: bool = False,
    failure_mode: str = "OTP_TIMEOUT",
) -> dict[str, Any]:
    provider = "pine_labs_identity_mock"

    if not applicant_has_seen_document:
        result = _fail(
            provider,
            "DOCUMENT_NOT_REVIEWED",
            "Applicant must see the document before eSign OTP is initiated.",
        )
        audit("esign_document", "mock", provider, applicant_id, "FAILED", "DOCUMENT_NOT_REVIEWED")
        return result

    if simulate_otp_failure:
        error_code = failure_mode if failure_mode in ("OTP_FAILED", "OTP_TIMEOUT") else "OTP_FAILED"
        result = _fail(
            provider,
            error_code,
            f"Mock OTP failure simulated ({error_code}). Not a real Aadhaar OTP.",
        )
        audit("esign_document", "mock", provider, applicant_id, "FAILED", error_code)
        return result

    rec = create_esign(applicant_id, document_hash, aadhaar_linked_mobile)
    result = _ok(
        provider,
        applicant_id=applicant_id,
        transaction_id=rec["transaction_id"],
        signed_document_id=rec["signed_document_id"],
        document_hash=document_hash,
        aadhaar_linked_mobile=mask_phone(aadhaar_linked_mobile),
        status="SIGNED",
        message="DEMO/MOCK: Aadhaar OTP eSign simulated. No actual Aadhaar eSign occurred.",
    )
    audit("esign_document", "mock", provider, applicant_id, "OK")
    return result


# ---------------------------------------------------------------------------
# E. collect_payment
# ---------------------------------------------------------------------------

def collect_payment(
    amount: float,
    applicant_id: str,
    purpose: str,
    currency: str = "INR",
    order_id: str | None = None,
    simulate_decline: bool = False,
) -> dict[str, Any]:
    provider = "pine_labs_payment_mock"

    if amount <= 0:
        result = _fail(provider, "INVALID_AMOUNT", "Amount must be greater than zero.")
        audit("collect_payment", "mock", provider, applicant_id, "FAILED", "INVALID_AMOUNT")
        return result

    rec = create_payment(amount, currency, purpose, applicant_id, order_id)

    if simulate_decline:
        set_payment_status(rec["transaction_id"], "DECLINED")
        result = _ok(
            provider,
            applicant_id=applicant_id,
            amount=amount,
            currency=currency,
            purpose=purpose,
            transaction_id=rec["transaction_id"],
            payment_link=f"https://raahi-demo.example/pay/{rec['transaction_id']}",
            status="DECLINED",
            message="DEMO/MOCK: Payment declined (simulation). No real money was charged.",
        )
        audit("collect_payment", "mock", provider, applicant_id, "DECLINED")
        return result

    result = _ok(
        provider,
        applicant_id=applicant_id,
        amount=amount,
        currency=currency,
        purpose=purpose,
        transaction_id=rec["transaction_id"],
        payment_link=f"https://raahi-demo.example/pay/{rec['transaction_id']}",
        status="PENDING",
        message="DEMO/MOCK: Payment link created. No real money will be charged.",
    )
    audit("collect_payment", "mock", provider, applicant_id, "OK")
    return result


# ---------------------------------------------------------------------------
# F. get_payment_status
# ---------------------------------------------------------------------------

def get_payment_status(
    transaction_id: str,
    force_status: str | None = None,
) -> dict[str, Any]:
    provider = "pine_labs_payment_mock"

    rec = get_payment(transaction_id)
    if rec is None:
        result = _fail(provider, "TRANSACTION_NOT_FOUND", f"No payment found for transaction_id {transaction_id}.")
        audit("get_payment_status", "mock", provider, None, "FAILED", "TRANSACTION_NOT_FOUND")
        return result

    if force_status:
        if force_status not in VALID_PAYMENT_STATES:
            return _fail(
                provider,
                "INVALID_STATUS",
                f"force_status must be one of {sorted(VALID_PAYMENT_STATES)}.",
            )
        set_payment_status(transaction_id, force_status)
        rec = get_payment(transaction_id)

    result = _ok(
        provider,
        transaction_id=transaction_id,
        amount=rec["amount"],
        currency=rec["currency"],
        purpose=rec["purpose"],
        status=rec["status"],
        created_at=rec["created_at"],
    )
    audit("get_payment_status", "mock", provider, rec.get("applicant_id"), "OK")
    return result


# ---------------------------------------------------------------------------
# G. issue_travel_insurance
# ---------------------------------------------------------------------------

def issue_travel_insurance(
    applicant_id: str,
    traveller_name: str,
    passport_number: str,
    destination: str,
    departure_date: str,
    return_date: str,
    coverage_amount: float,
    premium_amount: float,
    payment_transaction_id: str,
) -> dict[str, Any]:
    provider = "acko_insurance_mock"

    # Verify payment exists and succeeded (or at least not declined/failed)
    payment = get_payment(payment_transaction_id)
    if payment is None:
        result = _fail(provider, "PAYMENT_NOT_FOUND", "payment_transaction_id not found. Collect payment first.")
        audit("issue_travel_insurance", "mock", provider, applicant_id, "FAILED", "PAYMENT_NOT_FOUND")
        return result

    if payment["status"] in ("DECLINED", "FAILED"):
        result = _fail(
            provider,
            "PAYMENT_NOT_SUCCESSFUL",
            f"Payment status is {payment['status']}. Insurance cannot be issued.",
        )
        audit("issue_travel_insurance", "mock", provider, applicant_id, "FAILED", "PAYMENT_NOT_SUCCESSFUL")
        return result

    try:
        dep = date.fromisoformat(departure_date)
        ret = date.fromisoformat(return_date)
        if ret < dep:
            raise ValueError("return_date is before departure_date")
    except ValueError as e:
        result = _fail(provider, "INVALID_DATES", str(e))
        audit("issue_travel_insurance", "mock", provider, applicant_id, "FAILED", "INVALID_DATES")
        return result

    policy_data = {
        "applicant_id": applicant_id,
        "traveller_name": traveller_name,
        "passport_number": mask_passport(passport_number),
        "destination": destination,
        "departure_date": departure_date,
        "return_date": return_date,
        "coverage_amount": coverage_amount,
        "premium_amount": premium_amount,
        "payment_transaction_id": payment_transaction_id,
        "insurer": "ACKO (DEMO)",
        "status": "ISSUED",
        "certificate_type": "DEMO / MOCK INSURANCE CERTIFICATE",
    }
    rec = create_policy(policy_data)

    result = _ok(
        provider,
        applicant_id=applicant_id,
        policy_id=rec["policy_id"],
        certificate_url=f"https://raahi-demo.example/insurance/{rec['policy_id']}",
        insurer="ACKO (DEMO)",
        status="ISSUED",
        destination=destination,
        coverage_amount=coverage_amount,
        premium_amount=premium_amount,
        transaction_id=payment_transaction_id,
        certificate_type="DEMO / MOCK INSURANCE CERTIFICATE",
        message=(
            "DEMO/MOCK: This is NOT a real ACKO insurance policy. "
            "This mock certificate has no legal validity. For a real policy, use the ACKO connector."
        ),
    )
    audit("issue_travel_insurance", "mock", provider, applicant_id, "OK")
    return result


# ---------------------------------------------------------------------------
# H. request_bank_letter
# ---------------------------------------------------------------------------

def request_bank_letter(
    applicant_id: str,
    bank_name: str,
    account_reference: str,
    letter_purpose: str,
    required_date: str,
    delivery_method: str,
) -> dict[str, Any]:
    provider = "raahi_bank_letter_workflow_mock"

    data = {
        "applicant_id": applicant_id,
        "bank_name": bank_name,
        "account_reference": "****" + account_reference[-4:] if len(account_reference) >= 4 else "***",
        "letter_purpose": letter_purpose,
        "required_date": required_date,
        "delivery_method": delivery_method,
    }
    rec = create_bank_letter_request(data)

    result = _ok(
        provider,
        applicant_id=applicant_id,
        request_id=rec["request_id"],
        status="REQUESTED",
        message=(
            "DEMO/MOCK: Bank letter request queued for manual/voice/courier workflow. "
            "AA data has NOT been used as a substitute for a real bank-issued letter."
        ),
    )
    audit("request_bank_letter", "mock", provider, applicant_id, "OK")
    return result


# ---------------------------------------------------------------------------
# I. update_bank_letter_status
# ---------------------------------------------------------------------------

def update_bank_letter_status_tool(request_id: str, status: str) -> dict[str, Any]:
    provider = "raahi_bank_letter_workflow_mock"

    result_rec = update_bank_letter_status(request_id, status)
    if result_rec is None:
        result = _fail(provider, "REQUEST_NOT_FOUND", f"No bank letter request found for {request_id}.")
        audit("update_bank_letter_status", "mock", provider, None, "FAILED", "REQUEST_NOT_FOUND")
        return result

    if "error" in result_rec:
        result = _fail(
            provider,
            "INVALID_TRANSITION",
            result_rec["error"],
            allowed_transitions=result_rec.get("allowed"),
        )
        audit("update_bank_letter_status", "mock", provider, None, "FAILED", "INVALID_TRANSITION")
        return result

    result = _ok(
        provider,
        request_id=request_id,
        status=result_rec["status"],
        history=result_rec["history"],
    )
    audit("update_bank_letter_status", "mock", provider, result_rec.get("applicant_id"), "OK")
    return result


# ---------------------------------------------------------------------------
# J. check_serviceability_mock
# ---------------------------------------------------------------------------

def check_serviceability_mock(
    pickup_pincode: str,
    drop_pincode: str,
    mode: str = "surface",
) -> dict[str, Any]:
    provider = "delhivery_mock"

    metro_codes = {"110001", "400001", "560001", "700001", "600001", "500001", "380001"}
    serviceable = pickup_pincode in metro_codes or drop_pincode in metro_codes or True

    result = _ok(
        provider,
        pickup_pincode=pickup_pincode,
        drop_pincode=drop_pincode,
        transport_mode=mode,
        serviceable=serviceable,
        estimated_pickup_window="10:00–18:00 same day if booked before 12:00",
        message="DEMO/MOCK: Serviceability check simulated. Use mcp_delhivery_maps_krishramesh for real data.",
    )
    audit("check_serviceability_mock", "mock", provider, None, "OK")
    return result


# ---------------------------------------------------------------------------
# K. schedule_document_pickup_mock
# ---------------------------------------------------------------------------

def schedule_document_pickup_mock(
    pickup_address: str,
    drop_address: str,
    time_window: str,
    documents: list[str],
    applicant_id: str,
) -> dict[str, Any]:
    provider = "delhivery_mock"

    data = {
        "applicant_id": applicant_id,
        "pickup_address": pickup_address,
        "drop_address": drop_address,
        "time_window": time_window,
        "documents": documents,
    }
    rec = create_shipment(data)

    result = _ok(
        provider,
        applicant_id=applicant_id,
        awb=rec["awb"],
        chain_of_custody_id=rec["chain_of_custody_id"],
        pickup_confirmation=f"Pickup confirmed for window: {time_window}",
        status="PICKUP_SCHEDULED",
        message=(
            "DEMO/MOCK: No real courier pickup was scheduled. "
            "Originals are NOT marked as delivered until a confirming scan/status update."
        ),
    )
    audit("schedule_document_pickup_mock", "mock", provider, applicant_id, "OK")
    return result


# ---------------------------------------------------------------------------
# L. track_shipment_mock
# ---------------------------------------------------------------------------

def track_shipment_mock(awb: str) -> dict[str, Any]:
    provider = "delhivery_mock"

    rec = get_shipment(awb)
    if rec is None:
        result = _fail(provider, "AWB_NOT_FOUND", f"No shipment found for AWB {awb}.")
        audit("track_shipment_mock", "mock", provider, None, "FAILED", "AWB_NOT_FOUND")
        return result

    extra: dict[str, Any] = {}
    if rec["status"] == "NDR":
        extra["ndr_details"] = {
            "reason": "Access issue at pickup address (mock simulation)",
            "attempt_count": 1,
            "next_attempt": "Next business day",
        }

    result = _ok(
        provider,
        awb=awb,
        status=rec["status"],
        history=rec["history"],
        **extra,
        message="DEMO/MOCK: Shipment tracking simulated. Unknown AWB is never auto-converted to DELIVERED.",
    )
    audit("track_shipment_mock", "mock", provider, rec.get("applicant_id"), "OK")
    return result


# ---------------------------------------------------------------------------
# M. standardise_address_mock
# ---------------------------------------------------------------------------

def standardise_address_mock(address: str) -> dict[str, Any]:
    provider = "delhivery_maps_mock"

    parts = [p.strip() for p in address.split(",") if p.strip()]
    resolved = len(parts) >= 3

    structured: dict[str, Any] = {}
    unresolved: list[str] = []

    if resolved:
        structured = {
            "line1": parts[0] if len(parts) > 0 else None,
            "line2": parts[1] if len(parts) > 1 else None,
            "city": parts[2] if len(parts) > 2 else None,
            "state": parts[3] if len(parts) > 3 else None,
            "pincode": parts[-1] if parts[-1].isdigit() and len(parts[-1]) == 6 else None,
            "country": "IN",
        }
        if not structured["pincode"]:
            unresolved.append("pincode")
    else:
        unresolved = ["line1", "city", "state", "pincode"]

    result = _ok(
        provider,
        original_address=address,
        structured_address=structured,
        resolved=resolved,
        unresolved_fields=unresolved,
        geocode={"lat": 28.6139, "lon": 77.2090, "source": "mock"} if resolved else None,
        message=(
            "DEMO/MOCK: Address standardised using simple heuristic. "
            "Ambiguous result is NOT silently accepted. Use mcp_delhivery_maps_krishramesh for real geocoding."
        ),
    )
    audit("standardise_address_mock", "mock", provider, None, "OK")
    return result


# ---------------------------------------------------------------------------
# N. estimate_route_mock
# ---------------------------------------------------------------------------

def estimate_route_mock(
    origin: str,
    destination: str,
    vehicle_type: str = "bike",
) -> dict[str, Any]:
    provider = "delhivery_maps_mock"

    result = _ok(
        provider,
        origin=origin,
        destination=destination,
        vehicle_type=vehicle_type,
        distance_km=12.5,
        eta_minutes=35,
        route_summary="Mock route: origin → city centre → destination",
        message=(
            "DEMO/MOCK: Route estimate is a fixed placeholder value. "
            "Use mcp_delhivery_maps_krishramesh for real routing."
        ),
    )
    audit("estimate_route_mock", "mock", provider, None, "OK")
    return result


# ---------------------------------------------------------------------------
# O. get_demo_case
# ---------------------------------------------------------------------------

def get_demo_case(applicant_id: str | None = None) -> dict[str, Any]:
    from src.store import _store
    aid = applicant_id or DEMO_APPLICANT_ID
    applicant = _store["applicants"].get(aid, {})

    consents = {k: v for k, v in _store["consents"].items() if v.get("applicant_id") == aid}
    payments = {k: v for k, v in _store["payments"].items() if v.get("applicant_id") == aid}
    esigns = {k: v for k, v in _store["esign_transactions"].items() if v.get("applicant_id") == aid}
    policies = {k: v for k, v in _store["insurance_policies"].items() if v.get("applicant_id") == aid}
    bank_letters = {k: v for k, v in _store["bank_letter_requests"].items() if v.get("applicant_id") == aid}
    shipments = {k: v for k, v in _store["shipments"].items() if v.get("applicant_id") == aid}

    return {
        "success": True,
        "mode": "mock",
        "provider": "raahi_demo_store",
        "applicant": applicant,
        "consents": consents,
        "payments": payments,
        "esign_transactions": esigns,
        "insurance_policies": policies,
        "bank_letter_requests": bank_letters,
        "shipments": shipments,
    }


# ---------------------------------------------------------------------------
# P. reset_demo_case
# ---------------------------------------------------------------------------

def reset_demo_case(applicant_id: str | None = None) -> dict[str, Any]:
    aid = applicant_id or DEMO_APPLICANT_ID
    reset_demo(aid)
    result = {
        "success": True,
        "mode": "mock",
        "provider": "raahi_demo_store",
        "applicant_id": aid,
        "reset_at": now_iso(),
        "message": "Demo case reset. All mock records for this applicant have been cleared.",
    }
    audit("reset_demo_case", "mock", "raahi_demo_store", aid, "OK")
    return result


# ---------------------------------------------------------------------------
# Q. get_audit_log (tool wrapper)
# ---------------------------------------------------------------------------

def get_audit_log_tool(applicant_id: str | None = None) -> dict[str, Any]:
    events = get_audit_log(applicant_id)
    return {
        "success": True,
        "mode": "mock",
        "provider": "raahi_demo_store",
        "applicant_id": applicant_id,
        "total_events": len(events),
        "events": events,
    }

"""
In-memory demo store for the Raahi Auxiliary MCP.

Lives only for the server process lifetime.
Set DEMO_PERSISTENCE=true to log state changes to stderr (no real DB).
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Demo applicant seed
# ---------------------------------------------------------------------------

DEMO_APPLICANT_ID = "RAAHI-DEMO-001"

_DEMO_APPLICANT_SEED: dict[str, Any] = {
    "applicant_id": DEMO_APPLICANT_ID,
    "name": "Ananya Sharma",
    "mobile": "+919999999999",
    "destination": "France",
    "travel_type": "Educational group",
    "departure_date": "2026-11-10",
    "return_date": "2026-11-20",
}

# ---------------------------------------------------------------------------
# Demo PAN registry (deterministic, no real data)
# ---------------------------------------------------------------------------

DEMO_PAN_REGISTRY: dict[str, dict[str, Any]] = {
    "ABCDE1234F": {"name": "Ananya Sharma", "valid": True},
    "BCDEA2345G": {"name": "Rahul Mehta", "valid": True},
    "INVALID123": {"name": None, "valid": False},
}

# ---------------------------------------------------------------------------
# Valid document types for DigiLocker mock
# ---------------------------------------------------------------------------

SUPPORTED_DOC_TYPES = {"address_proof", "aadhaar", "passport", "driving_license"}

# ---------------------------------------------------------------------------
# Valid payment states
# ---------------------------------------------------------------------------

VALID_PAYMENT_STATES = {"PENDING", "SUCCESS", "DECLINED", "FAILED"}

# ---------------------------------------------------------------------------
# Valid bank-letter states and allowed transitions
# ---------------------------------------------------------------------------

BANK_LETTER_STATES = [
    "REQUESTED",
    "BANK_CONTACTED",
    "BANK_PROCESSING",
    "READY_FOR_PICKUP",
    "DISPATCHED",
    "COMPLETED",
    "FAILED",
]

BANK_LETTER_TRANSITIONS: dict[str, list[str]] = {
    "REQUESTED": ["BANK_CONTACTED", "FAILED"],
    "BANK_CONTACTED": ["BANK_PROCESSING", "FAILED"],
    "BANK_PROCESSING": ["READY_FOR_PICKUP", "FAILED"],
    "READY_FOR_PICKUP": ["DISPATCHED", "FAILED"],
    "DISPATCHED": ["COMPLETED", "FAILED"],
    "COMPLETED": [],
    "FAILED": [],
}

# ---------------------------------------------------------------------------
# Valid shipment states
# ---------------------------------------------------------------------------

SHIPMENT_STATES = [
    "CREATED",
    "PICKUP_SCHEDULED",
    "PICKED_UP",
    "IN_TRANSIT",
    "OUT_FOR_DELIVERY",
    "DELIVERED",
    "NDR",
]

# ---------------------------------------------------------------------------
# In-memory tables
# ---------------------------------------------------------------------------

_store: dict[str, Any] = {
    "applicants": {DEMO_APPLICANT_ID: dict(_DEMO_APPLICANT_SEED)},
    "consents": {},
    "payments": {},
    "esign_transactions": {},
    "insurance_policies": {},
    "bank_letter_requests": {},
    "shipments": {},
    "audit_log": [],
    # Mock connector stores
    "whatsapp_messages": [],       # whatsapp_raahi mock
    "aa_consents": {},             # banking_aa mock
    "aa_sessions": {},             # banking_aa mock
    "gnani_calls": {},             # mcp_raahi_gnani mock
    "gnani_transcriptions": {},    # mcp_raahi_gnani mock
    "pl_orders": {},               # pinelabs_plural mock
    "acko_policies": {},           # acko_insurance mock
    "identity_verifications": {},  # pine_labs_identity mock
    "delhivery_pickups": {},       # delhivery_shipment mock
    "delhivery_tracks": {},        # delhivery_shipment mock
}

_VERBOSE = os.environ.get("DEMO_PERSISTENCE", "").lower() == "true"


def _log(msg: str) -> None:
    if _VERBOSE:
        import sys
        print(f"[STORE] {msg}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def new_id(prefix: str = "") -> str:
    uid = str(uuid.uuid4()).upper()
    return f"{prefix}{uid}" if prefix else uid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

def create_consent(applicant_id: str, mobile: str, purpose: str, requested_documents: list[str]) -> dict[str, Any]:
    cid = new_id("CONSENT-")
    rec = {
        "consent_id": cid,
        "applicant_id": applicant_id,
        "mobile": mobile,
        "purpose": purpose,
        "requested_documents": requested_documents,
        "status": "PENDING",
        "created_at": now_iso(),
    }
    _store["consents"][cid] = rec
    _log(f"consent created {cid}")
    return rec


def get_consent(consent_id: str) -> dict[str, Any] | None:
    return _store["consents"].get(consent_id)


def activate_consent(consent_id: str) -> None:
    c = _store["consents"].get(consent_id)
    if c:
        c["status"] = "ACTIVE"
        _log(f"consent activated {consent_id}")


# ---------------------------------------------------------------------------
# Payments
# ---------------------------------------------------------------------------

def create_payment(amount: float, currency: str, purpose: str, applicant_id: str, order_id: str | None) -> dict[str, Any]:
    txn_id = new_id("TXN-")
    rec = {
        "transaction_id": txn_id,
        "order_id": order_id or new_id("ORD-"),
        "applicant_id": applicant_id,
        "amount": amount,
        "currency": currency,
        "purpose": purpose,
        "status": "PENDING",
        "created_at": now_iso(),
    }
    _store["payments"][txn_id] = rec
    _log(f"payment created {txn_id}")
    return rec


def get_payment(transaction_id: str) -> dict[str, Any] | None:
    return _store["payments"].get(transaction_id)


def set_payment_status(transaction_id: str, status: str) -> None:
    p = _store["payments"].get(transaction_id)
    if p and status in VALID_PAYMENT_STATES:
        p["status"] = status
        _log(f"payment {transaction_id} -> {status}")


# ---------------------------------------------------------------------------
# eSign
# ---------------------------------------------------------------------------

def create_esign(applicant_id: str, document_hash: str, mobile: str) -> dict[str, Any]:
    txn_id = new_id("ESIGN-")
    rec = {
        "transaction_id": txn_id,
        "applicant_id": applicant_id,
        "document_hash": document_hash,
        "signed_document_id": new_id("SDOC-"),
        "aadhaar_linked_mobile": _mask_phone(mobile),
        "status": "SIGNED",
        "created_at": now_iso(),
    }
    _store["esign_transactions"][txn_id] = rec
    _log(f"esign created {txn_id}")
    return rec


# ---------------------------------------------------------------------------
# Insurance
# ---------------------------------------------------------------------------

def create_policy(data: dict[str, Any]) -> dict[str, Any]:
    policy_id = new_id("POL-MOCK-")
    rec = {
        "policy_id": policy_id,
        **data,
        "created_at": now_iso(),
    }
    _store["insurance_policies"][policy_id] = rec
    _log(f"policy created {policy_id}")
    return rec


# ---------------------------------------------------------------------------
# Bank letter
# ---------------------------------------------------------------------------

def create_bank_letter_request(data: dict[str, Any]) -> dict[str, Any]:
    req_id = new_id("BLR-")
    rec = {
        "request_id": req_id,
        **data,
        "status": "REQUESTED",
        "history": [{"status": "REQUESTED", "at": now_iso()}],
        "created_at": now_iso(),
    }
    _store["bank_letter_requests"][req_id] = rec
    _log(f"bank_letter_request created {req_id}")
    return rec


def get_bank_letter_request(request_id: str) -> dict[str, Any] | None:
    return _store["bank_letter_requests"].get(request_id)


def update_bank_letter_status(request_id: str, new_status: str) -> dict[str, Any] | None:
    rec = _store["bank_letter_requests"].get(request_id)
    if rec is None:
        return None
    current = rec["status"]
    allowed = BANK_LETTER_TRANSITIONS.get(current, [])
    if new_status not in allowed:
        return {"error": f"Invalid transition {current} -> {new_status}", "allowed": allowed}
    rec["status"] = new_status
    rec["history"].append({"status": new_status, "at": now_iso()})
    _log(f"bank_letter {request_id} -> {new_status}")
    return rec


# ---------------------------------------------------------------------------
# Shipments
# ---------------------------------------------------------------------------

def create_shipment(data: dict[str, Any]) -> dict[str, Any]:
    awb = new_id("AWB-MOCK-")
    coc_id = new_id("COC-")
    rec = {
        "awb": awb,
        "chain_of_custody_id": coc_id,
        **data,
        "status": "PICKUP_SCHEDULED",
        "history": [{"status": "PICKUP_SCHEDULED", "at": now_iso()}],
        "created_at": now_iso(),
    }
    _store["shipments"][awb] = rec
    _log(f"shipment created {awb}")
    return rec


def get_shipment(awb: str) -> dict[str, Any] | None:
    return _store["shipments"].get(awb)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------

def audit(
    tool: str,
    mode: str,
    provider: str,
    applicant_id: str | None,
    result_status: str,
    error_code: str | None = None,
) -> None:
    _store["audit_log"].append({
        "event_id": new_id("EVT-"),
        "timestamp": now_iso(),
        "tool": tool,
        "mode": mode,
        "provider": provider,
        "applicant_id": applicant_id,
        "result_status": result_status,
        "error_code": error_code,
    })


def get_audit_log(applicant_id: str | None = None) -> list[dict[str, Any]]:
    log = _store["audit_log"]
    if applicant_id:
        log = [e for e in log if e.get("applicant_id") == applicant_id]
    return list(log)


# ---------------------------------------------------------------------------
# Demo reset
# ---------------------------------------------------------------------------

def reset_demo(applicant_id: str | None = None) -> None:
    aid = applicant_id or DEMO_APPLICANT_ID
    mock_tables = (
        "consents", "payments", "esign_transactions", "insurance_policies",
        "bank_letter_requests", "shipments",
        "aa_consents", "aa_sessions", "gnani_calls", "gnani_transcriptions",
        "pl_orders", "acko_policies", "identity_verifications",
        "delhivery_pickups", "delhivery_tracks",
    )
    for table in mock_tables:
        t = _store[table]
        if isinstance(t, dict):
            keys_to_remove = [k for k, v in t.items() if isinstance(v, dict) and v.get("applicant_id") == aid]
            for k in keys_to_remove:
                del t[k]
    _store["whatsapp_messages"] = [m for m in _store["whatsapp_messages"] if m.get("applicant_id") != aid]
    _store["applicants"][aid] = dict(_DEMO_APPLICANT_SEED)
    _log(f"demo reset for {aid}")


# ---------------------------------------------------------------------------
# Masking helpers
# ---------------------------------------------------------------------------

def _mask_phone(phone: str) -> str:
    if len(phone) >= 10:
        return phone[:3] + "******" + phone[-4:]
    return "***masked***"


def mask_pan(pan: str) -> str:
    if len(pan) >= 5:
        return pan[:4] + "****" + pan[-1:]
    return "***masked***"


def mask_passport(pp: str) -> str:
    if len(pp) >= 5:
        return pp[:3] + "****" + pp[-2:]
    return "***masked***"


def mask_phone(phone: str) -> str:
    return _mask_phone(phone)

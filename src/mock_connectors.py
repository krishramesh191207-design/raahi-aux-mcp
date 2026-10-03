"""
Mock implementations of the 7 external connectors used by Raahi.

Every function returns mode="mock" and a clear provider label.
NO external APIs are called.

Connectors mocked here:
  1. whatsapp_raahi        — WhatsApp messaging
  2. banking_aa            — Setu Account Aggregator (AA consent + data)
  3. mcp_raahi_gnani       — Gnani voice (STT, TTS, outbound calls, IVR)
  4. pinelabs_plural        — Pine Labs Plural payment orders
  5. acko_insurance        — ACKO travel insurance issuance
  6. pine_labs_identity    — Pine Labs Identity (PAN, DigiLocker, eSign)
  7. delhivery_shipment    — Delhivery Express pickup + tracking
"""

from __future__ import annotations

import base64
import re
from datetime import date, datetime, timezone
from typing import Any

from src.store import (
    DEMO_APPLICANT_ID,
    DEMO_PAN_REGISTRY,
    SUPPORTED_DOC_TYPES,
    _store,
    audit,
    get_consent,
    get_payment,
    mask_pan,
    mask_passport,
    mask_phone,
    new_id,
    now_iso,
)

_PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")


def _ok(provider: str, **kwargs: Any) -> dict[str, Any]:
    return {"success": True, "mode": "mock", "provider": provider, **kwargs}


def _fail(provider: str, error_code: str, message: str, **kwargs: Any) -> dict[str, Any]:
    return {"success": False, "mode": "mock", "provider": provider,
            "error_code": error_code, "message": message, **kwargs}


# ===========================================================================
# 1. whatsapp_raahi
# ===========================================================================

def wa_send_message(
    to: str,
    message: str,
    applicant_id: str = "",
    message_type: str = "text",
    media_url: str = "",
) -> dict[str, Any]:
    provider = "whatsapp_raahi_mock"
    msg_id = new_id("WA-")
    rec = {
        "message_id": msg_id,
        "to": mask_phone(to) if to else "unknown",
        "message_type": message_type,
        "preview": message[:120] + ("..." if len(message) > 120 else ""),
        "media_url": media_url,
        "applicant_id": applicant_id,
        "status": "SENT",
        "sent_at": now_iso(),
    }
    _store["whatsapp_messages"].append(rec)
    audit("wa_send_message", "mock", provider, applicant_id or None, "OK")
    return _ok(provider, message_id=msg_id, to=rec["to"], status="SENT",
               message="DEMO/MOCK: WhatsApp message simulated. Not sent via real WhatsApp Business API.")


def wa_send_template(
    to: str,
    template_name: str,
    parameters: dict,
    applicant_id: str = "",
) -> dict[str, Any]:
    provider = "whatsapp_raahi_mock"
    msg_id = new_id("WA-TPL-")
    rec = {
        "message_id": msg_id,
        "to": mask_phone(to) if to else "unknown",
        "template_name": template_name,
        "parameters": parameters,
        "applicant_id": applicant_id,
        "status": "SENT",
        "sent_at": now_iso(),
    }
    _store["whatsapp_messages"].append(rec)
    audit("wa_send_template", "mock", provider, applicant_id or None, "OK")
    return _ok(provider, message_id=msg_id, template_name=template_name, status="SENT",
               message="DEMO/MOCK: WhatsApp template message simulated.")


def wa_get_message_status(message_id: str) -> dict[str, Any]:
    provider = "whatsapp_raahi_mock"
    msgs = [m for m in _store["whatsapp_messages"] if m.get("message_id") == message_id]
    if not msgs:
        return _fail(provider, "MESSAGE_NOT_FOUND", f"No message found with id {message_id}")
    m = msgs[0]
    return _ok(provider, message_id=message_id, status=m["status"], sent_at=m["sent_at"])


# ===========================================================================
# 2. banking_aa  (Setu Account Aggregator)
# ===========================================================================

def aa_request_consent(
    vua: str,
    purpose: str = "Visa financial verification",
    data_range_months: int = 6,
    applicant_id: str = "",
) -> dict[str, Any]:
    provider = "banking_aa_mock"
    consent_id = new_id("AA-CONSENT-")
    rec = {
        "consent_id": consent_id,
        "vua": vua,
        "purpose": purpose,
        "data_range_months": data_range_months,
        "applicant_id": applicant_id,
        "status": "PENDING",
        "consent_url": f"https://raahi-demo.example/aa-consent/{consent_id}",
        "created_at": now_iso(),
    }
    _store["aa_consents"][consent_id] = rec
    audit("aa_request_consent", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        consent_id=consent_id,
        status="PENDING",
        consent_url=rec["consent_url"],
        message="DEMO/MOCK: AA consent request created. Not a real Setu AA consent.",
    )


def aa_get_consent_status(consent_id: str, force_status: str = "") -> dict[str, Any]:
    provider = "banking_aa_mock"
    rec = _store["aa_consents"].get(consent_id)
    if not rec:
        return _fail(provider, "CONSENT_NOT_FOUND", f"No AA consent found for {consent_id}")
    if force_status in ("PENDING", "ACTIVE", "REJECTED", "EXPIRED"):
        rec["status"] = force_status
    return _ok(provider, consent_id=consent_id, status=rec["status"],
               vua=rec["vua"], created_at=rec["created_at"])


def aa_fetch_bank_data(
    consent_id: str,
    data_range_months: int = 6,
    applicant_id: str = "",
) -> dict[str, Any]:
    provider = "banking_aa_mock"
    rec = _store["aa_consents"].get(consent_id)
    if not rec:
        return _fail(provider, "CONSENT_NOT_FOUND", "AA consent not found.")
    if rec["status"] not in ("ACTIVE", "PENDING"):
        return _fail(provider, "CONSENT_NOT_ACTIVE",
                     f"Consent status is {rec['status']}. Cannot fetch data.")

    session_id = new_id("AA-SESSION-")
    session = {
        "session_id": session_id,
        "consent_id": consent_id,
        "applicant_id": applicant_id,
        "created_at": now_iso(),
        "accounts": [
            {
                "fip": "HDFC Bank (mock)",
                "account_type": "SAVINGS",
                "masked_account": "****4321",
                "balance": 125000.00,
                "currency": "INR",
            }
        ],
        "transactions": [
            {"date": "2026-09-01", "description": "Salary credit", "amount": 85000, "type": "CREDIT"},
            {"date": "2026-09-10", "description": "Rent", "amount": -28000, "type": "DEBIT"},
            {"date": "2026-09-20", "description": "Grocery", "amount": -4500, "type": "DEBIT"},
            {"date": "2026-10-01", "description": "Salary credit", "amount": 85000, "type": "CREDIT"},
        ],
        "income_signal": {"monthly_avg_credit": 85000, "currency": "INR"},
        "spend_signal": {"monthly_avg_debit": 35000, "currency": "INR"},
    }
    _store["aa_sessions"][session_id] = session
    audit("aa_fetch_bank_data", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        session_id=session_id,
        consent_id=consent_id,
        accounts=session["accounts"],
        transactions=session["transactions"],
        income_signal=session["income_signal"],
        spend_signal=session["spend_signal"],
        message=(
            "DEMO/MOCK: Bank data simulated. "
            "This is NOT real AA data. AA data must NOT be used as a bank-issued letter."
        ),
    )


# ===========================================================================
# 3. mcp_raahi_gnani  (Gnani Voice)
# ===========================================================================

def gnani_transcribe_speech(
    audio_base64: str,
    language_code: str = "en-IN",
    applicant_id: str = "",
    simulate_failure: bool = False,
) -> dict[str, Any]:
    provider = "gnani_stt_mock"
    if simulate_failure:
        audit("gnani_transcribe_speech", "mock", provider, applicant_id or None, "FAILED", "STT_ERROR")
        return _fail(provider, "STT_ERROR", "Mock STT partial transcript error.")

    txn_id = new_id("STT-")
    transcript = "I need a France visa for November 10th to 20th for an educational group trip."
    rec = {"txn_id": txn_id, "applicant_id": applicant_id,
           "language_code": language_code, "transcript": transcript, "created_at": now_iso()}
    _store["gnani_transcriptions"][txn_id] = rec
    audit("gnani_transcribe_speech", "mock", provider, applicant_id or None, "OK")
    return _ok(provider, txn_id=txn_id, transcript=transcript, language_code=language_code,
               confidence=0.97, is_final=True,
               message="DEMO/MOCK: Fixed demo transcript returned. No real audio processed.")


def gnani_speak_reply(
    text: str,
    language: str = "en-IN",
    voice: str = "Nalini",
    applicant_id: str = "",
) -> dict[str, Any]:
    provider = "gnani_tts_mock"
    audio_b64 = base64.b64encode(b"MOCK_AUDIO_BYTES").decode()
    audit("gnani_speak_reply", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        audio_base64=audio_b64,
        content_type="audio/wav",
        text_preview=text[:100],
        language=language,
        voice=voice,
        message="DEMO/MOCK: Audio is placeholder bytes. No real TTS synthesis performed.",
    )


def gnani_call_bank_rm(
    bot_id: str,
    phone: str,
    country_code: str,
    name: str,
    checklist_item_id: str = "",
    applicant_id: str = "",
    simulate_failure: bool = False,
) -> dict[str, Any]:
    provider = "gnani_call_mock"
    if simulate_failure:
        audit("gnani_call_bank_rm", "mock", provider, applicant_id or None, "FAILED", "UNWHITELISTED_NUMBER")
        return _fail(provider, "UNWHITELISTED_NUMBER",
                     "Phone number is not whitelisted for outbound calls (mock simulation).")

    call_id = new_id("CALL-")
    conv_id = new_id("CONV-")
    rec = {
        "call_id": call_id,
        "conversation_id": conv_id,
        "bot_id": bot_id,
        "phone": mask_phone(phone),
        "country_code": country_code,
        "name": name,
        "checklist_item_id": checklist_item_id,
        "applicant_id": applicant_id,
        "status": "INITIATED",
        "created_at": now_iso(),
    }
    _store["gnani_calls"][call_id] = rec
    audit("gnani_call_bank_rm", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        call_id=call_id,
        conversation_id=conv_id,
        status="INITIATED",
        phone=mask_phone(phone),
        message="DEMO/MOCK: Outbound call simulated. No real call was placed.",
    )


def gnani_read_call_outcome(
    conversation_id: str,
    force_disposition: str = "",
) -> dict[str, Any]:
    provider = "gnani_call_mock"
    calls = [c for c in _store["gnani_calls"].values() if c.get("conversation_id") == conversation_id]
    if not calls:
        return _fail(provider, "CONVERSATION_NOT_FOUND", f"No call found for conversation_id {conversation_id}")

    disposition = force_disposition if force_disposition in (
        "CONNECTED_RESOLVED", "CONNECTED_PENDING", "NO_ANSWER", "VOICEMAIL", "FAILED"
    ) else "CONNECTED_RESOLVED"

    return _ok(
        provider,
        conversation_id=conversation_id,
        status="COMPLETED",
        disposition=disposition,
        transcript="[MOCK] Agent: Hello, I'm calling on behalf of Ananya Sharma regarding a bank statement. "
                   "Bank RM: Sure, we'll have it ready by Thursday.",
        resolved=disposition == "CONNECTED_RESOLVED",
        message="DEMO/MOCK: Fixed mock transcript. Checklist item resolved only on CONNECTED_RESOLVED disposition.",
    )


def gnani_navigate_ivr(
    bot_id: str,
    dtmf_sequence: str,
    applicant_id: str = "",
) -> dict[str, Any]:
    provider = "gnani_ivr_mock"
    if not re.match(r"^[0-9#*]+$", dtmf_sequence):
        return _fail(provider, "INVALID_DTMF", "DTMF sequence contains invalid characters.")
    audit("gnani_navigate_ivr", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        bot_id=bot_id,
        dtmf_sequence=dtmf_sequence,
        registered=True,
        message="DEMO/MOCK: DTMF tones simulated. Never guesses unmapped IVR menu options.",
    )


def gnani_pull_case_status(
    applicant_id: str,
    case_id: str = "",
) -> dict[str, Any]:
    provider = "gnani_case_mock"
    app = _store["applicants"].get(applicant_id or DEMO_APPLICANT_ID, {})
    checklist = {
        "passport": "VERIFIED",
        "bank_statement": "PENDING",
        "travel_insurance": "NOT_STARTED",
        "visa_fee": "NOT_STARTED",
        "address_proof": "VERIFIED",
    }
    audit("gnani_pull_case_status", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        applicant_id=applicant_id,
        name=app.get("name", "Unknown"),
        destination=app.get("destination", "Unknown"),
        checklist=checklist,
        overall_status="IN_PROGRESS",
        message="DEMO/MOCK: Fixed mock checklist status injected into call context.",
    )


# ===========================================================================
# 4. pinelabs_plural  (Pine Labs Plural payment orders)
# ===========================================================================

def pl_create_order(
    amount: float,
    currency: str = "INR",
    purpose: str = "",
    applicant_id: str = "",
    simulate_failure: bool = False,
) -> dict[str, Any]:
    provider = "pinelabs_plural_mock"
    if amount <= 0:
        return _fail(provider, "INVALID_AMOUNT", "Amount must be greater than zero.")
    if simulate_failure:
        audit("pl_create_order", "mock", provider, applicant_id or None, "FAILED", "ORDER_CREATION_FAILED")
        return _fail(provider, "ORDER_CREATION_FAILED", "Mock order creation failure.")

    order_id = new_id("PLO-")
    txn_id = new_id("PLTXN-")
    rec = {
        "order_id": order_id,
        "transaction_id": txn_id,
        "amount": amount,
        "currency": currency,
        "purpose": purpose,
        "applicant_id": applicant_id,
        "status": "CREATED",
        "payment_link": f"https://raahi-demo.example/plural-pay/{order_id}",
        "created_at": now_iso(),
    }
    _store["pl_orders"][order_id] = rec
    audit("pl_create_order", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        order_id=order_id,
        transaction_id=txn_id,
        amount=amount,
        currency=currency,
        payment_link=rec["payment_link"],
        status="CREATED",
        message="DEMO/MOCK: Pine Labs Plural order created. No real payment processed.",
    )


def pl_get_order_status(
    order_id: str,
    force_status: str = "",
) -> dict[str, Any]:
    provider = "pinelabs_plural_mock"
    rec = _store["pl_orders"].get(order_id)
    if not rec:
        return _fail(provider, "ORDER_NOT_FOUND", f"No order found for {order_id}")
    valid_states = {"CREATED", "PENDING", "SUCCESS", "DECLINED", "FAILED", "REFUNDED"}
    if force_status and force_status in valid_states:
        rec["status"] = force_status
    return _ok(
        provider,
        order_id=order_id,
        transaction_id=rec["transaction_id"],
        amount=rec["amount"],
        currency=rec["currency"],
        status=rec["status"],
        created_at=rec["created_at"],
    )


def pl_refund_order(order_id: str, reason: str = "") -> dict[str, Any]:
    provider = "pinelabs_plural_mock"
    rec = _store["pl_orders"].get(order_id)
    if not rec:
        return _fail(provider, "ORDER_NOT_FOUND", f"No order found for {order_id}")
    if rec["status"] != "SUCCESS":
        return _fail(provider, "REFUND_NOT_ALLOWED",
                     f"Cannot refund order in status {rec['status']}. Only SUCCESS orders can be refunded.")
    rec["status"] = "REFUNDED"
    audit("pl_refund_order", "mock", provider, rec.get("applicant_id"), "OK")
    return _ok(provider, order_id=order_id, status="REFUNDED", reason=reason,
               message="DEMO/MOCK: Refund simulated. No real money movement.")


# ===========================================================================
# 5. acko_insurance
# ===========================================================================

def acko_get_quote(
    destination: str,
    departure_date: str,
    return_date: str,
    traveller_count: int = 1,
    applicant_id: str = "",
) -> dict[str, Any]:
    provider = "acko_insurance_mock"
    try:
        dep = date.fromisoformat(departure_date)
        ret = date.fromisoformat(return_date)
        days = (ret - dep).days
        if days <= 0:
            raise ValueError("return_date must be after departure_date")
    except ValueError as e:
        return _fail(provider, "INVALID_DATES", str(e))

    premium = round(299 * traveller_count + days * 15, 2)
    coverage = 500000 * traveller_count
    quote_id = new_id("ACKO-Q-")
    audit("acko_get_quote", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        quote_id=quote_id,
        destination=destination,
        departure_date=departure_date,
        return_date=return_date,
        traveller_count=traveller_count,
        trip_days=days,
        premium_inr=premium,
        coverage_inr=coverage,
        plan_name="Raahi Travel Shield (DEMO)",
        message="DEMO/MOCK: Insurance quote is a fixed formula. Not a real ACKO quote.",
    )


def acko_issue_policy(
    applicant_id: str,
    traveller_name: str,
    passport_number: str,
    destination: str,
    departure_date: str,
    return_date: str,
    coverage_amount: float,
    premium_amount: float,
    payment_order_id: str,
    simulate_failure: bool = False,
) -> dict[str, Any]:
    provider = "acko_insurance_mock"

    order = _store["pl_orders"].get(payment_order_id)
    # Also check the existing payments table for backwards compat
    from src.store import get_payment
    payment = order or get_payment(payment_order_id)
    if not payment:
        return _fail(provider, "PAYMENT_NOT_FOUND",
                     "payment_order_id not found. Create a Plural order or collect_payment first.")
    if payment.get("status") in ("DECLINED", "FAILED"):
        return _fail(provider, "PAYMENT_NOT_SUCCESSFUL",
                     f"Payment status is {payment['status']}. Cannot issue policy.")

    if simulate_failure:
        return _fail(provider, "POLICY_ISSUANCE_FAILED",
                     "Mock ACKO policy issuance failure (simulation).")

    try:
        dep = date.fromisoformat(departure_date)
        ret = date.fromisoformat(return_date)
        if ret < dep:
            raise ValueError("return_date before departure_date")
    except ValueError as e:
        return _fail(provider, "INVALID_DATES", str(e))

    policy_id = new_id("ACKO-POL-")
    rec = {
        "policy_id": policy_id,
        "applicant_id": applicant_id,
        "traveller_name": traveller_name,
        "passport_number": mask_passport(passport_number),
        "destination": destination,
        "departure_date": departure_date,
        "return_date": return_date,
        "coverage_amount": coverage_amount,
        "premium_amount": premium_amount,
        "payment_order_id": payment_order_id,
        "status": "ISSUED",
        "certificate_type": "DEMO / MOCK INSURANCE CERTIFICATE",
        "created_at": now_iso(),
    }
    _store["acko_policies"][policy_id] = rec
    audit("acko_issue_policy", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        policy_id=policy_id,
        certificate_url=f"https://raahi-demo.example/acko/{policy_id}",
        insurer="ACKO General Insurance (DEMO)",
        status="ISSUED",
        destination=destination,
        coverage_amount=coverage_amount,
        premium_amount=premium_amount,
        certificate_type="DEMO / MOCK INSURANCE CERTIFICATE",
        message="DEMO/MOCK: NOT a real ACKO policy. Has no legal validity.",
    )


def acko_get_policy(policy_id: str) -> dict[str, Any]:
    provider = "acko_insurance_mock"
    rec = _store["acko_policies"].get(policy_id)
    if not rec:
        return _fail(provider, "POLICY_NOT_FOUND", f"No policy found for {policy_id}")
    return _ok(provider, **{k: v for k, v in rec.items() if k != "applicant_id"},
               certificate_url=f"https://raahi-demo.example/acko/{policy_id}")


# ===========================================================================
# 6. pine_labs_identity  (PAN, DigiLocker, eSign)
# ===========================================================================

def pli_verify_pan(
    pan: str,
    expected_name: str = "",
    simulate_failure: bool = False,
) -> dict[str, Any]:
    provider = "pine_labs_identity_mock"
    pan = pan.strip().upper()
    if simulate_failure:
        audit("pli_verify_pan", "mock", provider, None, "FAILED", "NSDL_UNAVAILABLE")
        return _fail(provider, "NSDL_UNAVAILABLE", "PAN verification service temporarily unavailable (NSDL mock outage).")
    if not _PAN_RE.match(pan):
        audit("pli_verify_pan", "mock", provider, None, "FAILED", "INVALID_PAN_FORMAT")
        return _fail(provider, "INVALID_PAN_FORMAT", f"PAN format invalid. masked: {mask_pan(pan)}")

    entry = DEMO_PAN_REGISTRY.get(pan, {"name": "Demo Holder", "valid": True})
    name_match = None
    if expected_name and entry.get("name"):
        name_match = expected_name.strip().lower() == entry["name"].lower()

    vid = new_id("PAN-VER-")
    _store["identity_verifications"][vid] = {"type": "pan", "masked_pan": mask_pan(pan), "result": entry["valid"]}
    audit("pli_verify_pan", "mock", provider, None, "OK")
    return _ok(
        provider,
        verification_id=vid,
        valid=entry["valid"],
        name_match=name_match,
        registered_name=entry.get("name"),
        masked_pan=mask_pan(pan),
        message="DEMO/MOCK: PAN verified against mock registry only. Not real NSDL.",
    )


def pli_fetch_digilocker_doc(
    consent_id: str,
    document_type: str,
    applicant_id: str,
    simulate_unavailable: bool = False,
) -> dict[str, Any]:
    provider = "pine_labs_identity_mock"
    if not consent_id:
        return _fail(provider, "CONSENT_REQUIRED", "consent_id required. Never fetch without consent.")
    consent = get_consent(consent_id)
    if not consent:
        return _fail(provider, "CONSENT_NOT_FOUND", "Consent record not found.")
    doc_type = document_type.lower()
    if doc_type not in SUPPORTED_DOC_TYPES:
        return _fail(provider, "UNSUPPORTED_DOC_TYPE", f"Unsupported: {doc_type}")
    if doc_type not in (consent.get("requested_documents") or []):
        return _fail(provider, "DOC_NOT_IN_CONSENT", f"{doc_type} not in original consent.")
    if simulate_unavailable:
        return _fail(provider, "DOCUMENT_UNAVAILABLE", "Document unavailable in DigiLocker (mock).")
    doc_id = new_id("DL-MOCK-")
    audit("pli_fetch_digilocker_doc", "mock", provider, applicant_id, "OK")
    return _ok(
        provider,
        applicant_id=applicant_id,
        consent_id=consent_id,
        document_type=doc_type,
        document_id=doc_id,
        document_status="verified",
        document_url=f"https://raahi-demo.example/digilocker/{doc_id}",
        message="DEMO/MOCK: Mock DigiLocker document. Not a real government document.",
    )


def pli_esign_document(
    document_hash: str,
    aadhaar_linked_mobile: str,
    applicant_id: str,
    applicant_has_seen_document: bool,
    simulate_otp_failure: bool = False,
) -> dict[str, Any]:
    provider = "pine_labs_identity_mock"
    if not applicant_has_seen_document:
        return _fail(provider, "DOCUMENT_NOT_REVIEWED",
                     "Applicant must see the document before eSign OTP is initiated.")
    if simulate_otp_failure:
        audit("pli_esign_document", "mock", provider, applicant_id, "FAILED", "OTP_TIMEOUT")
        return _fail(provider, "OTP_TIMEOUT", "Mock OTP timeout. No real Aadhaar eSign attempted.")
    txn_id = new_id("ESIGN-PLI-")
    signed_id = new_id("SDOC-")
    rec = {
        "transaction_id": txn_id, "signed_document_id": signed_id,
        "document_hash": document_hash,
        "mobile": mask_phone(aadhaar_linked_mobile),
        "applicant_id": applicant_id, "status": "SIGNED", "created_at": now_iso(),
    }
    _store["identity_verifications"][txn_id] = rec
    audit("pli_esign_document", "mock", provider, applicant_id, "OK")
    return _ok(
        provider,
        transaction_id=txn_id,
        signed_document_id=signed_id,
        document_hash=document_hash,
        status="SIGNED",
        message="DEMO/MOCK: Aadhaar OTP eSign simulated. No actual eSign occurred.",
    )


# ===========================================================================
# 7. delhivery_shipment  (Express pickup + tracking)
# ===========================================================================

def delhivery_check_serviceability(
    pickup_pincode: str,
    drop_pincode: str,
    mode: str = "surface",
) -> dict[str, Any]:
    provider = "delhivery_shipment_mock"
    metros = {"110001", "400001", "560001", "700001", "600001", "500001", "380001"}
    serviceable = (pickup_pincode in metros or drop_pincode in metros or
                   (pickup_pincode.isdigit() and drop_pincode.isdigit()))
    audit("delhivery_check_serviceability", "mock", provider, None, "OK")
    return _ok(
        provider,
        pickup_pincode=pickup_pincode,
        drop_pincode=drop_pincode,
        mode=mode,
        serviceable=serviceable,
        estimated_pickup_window="10:00–18:00 same-day if booked before 12:00",
        message="DEMO/MOCK: Serviceability simulated. Use native Delhivery connector for real data.",
    )


def delhivery_schedule_pickup(
    pickup_address: str,
    drop_address: str,
    pickup_pincode: str,
    drop_pincode: str,
    time_window: str,
    documents: list[str],
    applicant_id: str = "",
    simulate_failure: bool = False,
) -> dict[str, Any]:
    provider = "delhivery_shipment_mock"
    if simulate_failure:
        return _fail(provider, "PICKUP_FAILED", "Mock pickup scheduling failure.")

    awb = new_id("AWB-DLV-")
    coc = new_id("COC-")
    rec = {
        "awb": awb,
        "chain_of_custody_id": coc,
        "pickup_address": pickup_address,
        "drop_address": drop_address,
        "pickup_pincode": pickup_pincode,
        "drop_pincode": drop_pincode,
        "time_window": time_window,
        "documents": documents,
        "applicant_id": applicant_id,
        "status": "PICKUP_SCHEDULED",
        "history": [{"status": "PICKUP_SCHEDULED", "at": now_iso()}],
        "created_at": now_iso(),
    }
    _store["delhivery_pickups"][awb] = rec
    audit("delhivery_schedule_pickup", "mock", provider, applicant_id or None, "OK")
    return _ok(
        provider,
        awb=awb,
        chain_of_custody_id=coc,
        pickup_confirmation=f"Pickup confirmed for {time_window}",
        status="PICKUP_SCHEDULED",
        message="DEMO/MOCK: No real courier pickup scheduled. Originals not marked delivered without confirming scan.",
    )


def delhivery_track_shipment(
    awb: str,
    force_status: str = "",
) -> dict[str, Any]:
    provider = "delhivery_shipment_mock"
    valid_states = {"CREATED", "PICKUP_SCHEDULED", "PICKED_UP", "IN_TRANSIT",
                    "OUT_FOR_DELIVERY", "DELIVERED", "NDR"}

    rec = _store["delhivery_pickups"].get(awb)
    if not rec:
        return _fail(provider, "AWB_NOT_FOUND",
                     f"No shipment found for AWB {awb}. Unknown AWBs never auto-converted to DELIVERED.")

    if force_status and force_status in valid_states:
        rec["status"] = force_status
        rec["history"].append({"status": force_status, "at": now_iso()})

    extra: dict[str, Any] = {}
    if rec["status"] == "NDR":
        extra["ndr_details"] = {
            "reason": "Access issue at address (mock)",
            "attempt_count": 1,
            "next_attempt": "Next business day",
        }

    audit("delhivery_track_shipment", "mock", provider, rec.get("applicant_id"), "OK")
    return _ok(
        provider,
        awb=awb,
        status=rec["status"],
        history=rec["history"],
        **extra,
        message="DEMO/MOCK: Shipment tracking simulated.",
    )

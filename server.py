"""
Raahi Auxiliary MCP Server — server.py

Run locally:
    uvicorn server:app --host 0.0.0.0 --port 8000

MCP endpoint: /mcp
Health endpoint: /health
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from mcp.server.mcpserver import MCPServer
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from src import tools as T
from src import mock_connectors as MC

# ---------------------------------------------------------------------------
# MCPServer setup
# ---------------------------------------------------------------------------

mcp = MCPServer(
    name="Raahi Auxiliary MCP",
    description=(
        "DEMO/MOCK auxiliary tool rail for the Raahi visa workflow. "
        "Provides mock implementations of identity, payment, insurance, logistics, "
        "and document tools not covered by native AgenticOrg connectors. "
        "NONE of these tools call real government, bank, or insurance services."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Tool registrations
# ---------------------------------------------------------------------------

@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates Pine Labs Identity PAN verification for the Raahi competition workflow. "
        "Does not call NSDL or Pine Labs. Never use this result as real government verification. "
        "Demo PANs: ABCDE1234F (valid, Ananya Sharma), BCDEA2345G (valid, Rahul Mehta), INVALID123 (invalid). "
        "Set simulate_failure=true to simulate an NSDL outage."
    )
)
async def verify_pan(
    pan: str,
    expected_name: str = "",
    simulate_failure: bool = False,
) -> dict:
    """Verify a PAN against the mock registry. Never calls NSDL."""
    return T.verify_pan(pan, expected_name or None, simulate_failure)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates a consent-bound DigiLocker document retrieval. "
        "Does not call DigiLocker. Requires a valid consent_id from create_digilocker_consent. "
        "Supported document types: address_proof, aadhaar, passport, driving_license. "
        "Set simulate_unavailable=true to simulate a document-not-found error."
    )
)
async def fetch_digilocker_doc(
    consent_id: str,
    document_type: str,
    applicant_id: str,
    simulate_unavailable: bool = False,
) -> dict:
    """Fetch a mock DigiLocker document under an existing consent."""
    return T.fetch_digilocker_doc(consent_id, document_type, applicant_id, simulate_unavailable)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Creates a mock DigiLocker consent record. "
        "Returns a consent_id and a demo consent URL. "
        "The consent URL is not a real DigiLocker URL. "
        "requested_documents must be from: address_proof, aadhaar, passport, driving_license."
    )
)
async def create_digilocker_consent(
    applicant_id: str,
    mobile: str,
    purpose: str,
    requested_documents: list[str],
) -> dict:
    """Create a mock DigiLocker consent for the given applicant."""
    return T.create_digilocker_consent(applicant_id, mobile, purpose, requested_documents)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates Aadhaar OTP eSign via Pine Labs Identity. "
        "Does not perform a real Aadhaar eSign. "
        "applicant_has_seen_document MUST be true — eSign is blocked if false. "
        "Set simulate_otp_failure=true to simulate OTP failure. "
        "failure_mode: OTP_FAILED | OTP_TIMEOUT."
    )
)
async def esign_document(
    document_hash: str,
    aadhaar_linked_mobile: str,
    applicant_id: str,
    applicant_has_seen_document: bool,
    simulate_otp_failure: bool = False,
    failure_mode: str = "OTP_TIMEOUT",
) -> dict:
    """Mock Aadhaar OTP eSign. Blocked unless applicant has seen the document."""
    return T.esign_document(
        document_hash, aadhaar_linked_mobile, applicant_id,
        applicant_has_seen_document, simulate_otp_failure, failure_mode
    )


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates payment link creation via Pine Labs Payment Gateway. "
        "Does not charge real money. Returns a mock payment link and transaction_id. "
        "Set simulate_decline=true to simulate a declined payment."
    )
)
async def collect_payment(
    amount: float,
    applicant_id: str,
    purpose: str,
    currency: str = "INR",
    order_id: str = "",
    simulate_decline: bool = False,
) -> dict:
    """Create a mock payment link. Never charges real money."""
    return T.collect_payment(amount, applicant_id, purpose, currency, order_id or None, simulate_decline)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Returns the status of a mock payment transaction. "
        "States: PENDING, SUCCESS, DECLINED, FAILED. "
        "Use force_status to advance the demo state."
    )
)
async def get_payment_status(
    transaction_id: str,
    force_status: str = "",
) -> dict:
    """Get or advance the status of a mock payment."""
    return T.get_payment_status(transaction_id, force_status or None)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates travel insurance issuance for the Raahi demo. "
        "Does not create a legally valid insurance policy. "
        "The certificate is labelled DEMO/MOCK INSURANCE CERTIFICATE. "
        "Requires a valid payment_transaction_id from collect_payment (status must not be DECLINED/FAILED). "
        "Provider: ACKO (DEMO). Not a real ACKO policy."
    )
)
async def issue_travel_insurance(
    applicant_id: str,
    traveller_name: str,
    passport_number: str,
    destination: str,
    departure_date: str,
    return_date: str,
    coverage_amount: float,
    premium_amount: float,
    payment_transaction_id: str,
) -> dict:
    """Issue a mock ACKO travel insurance certificate. Not legally valid."""
    return T.issue_travel_insurance(
        applicant_id, traveller_name, passport_number, destination,
        departure_date, return_date, coverage_amount, premium_amount, payment_transaction_id
    )


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates requesting a bank letter via the Raahi VoiceChase+CourierPickup workflow. "
        "This is the MISSING capability from the KEN case — AA data is NOT converted to a fake bank letter. "
        "The request is queued for manual/voice/courier follow-up. "
        "Valid delivery methods: courier, digital, branch_pickup."
    )
)
async def request_bank_letter(
    applicant_id: str,
    bank_name: str,
    account_reference: str,
    letter_purpose: str,
    required_date: str,
    delivery_method: str,
) -> dict:
    """Queue a bank letter request via the mock workflow (VoiceChase + courier)."""
    return T.request_bank_letter(
        applicant_id, bank_name, account_reference, letter_purpose, required_date, delivery_method
    )


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Updates the status of a mock bank letter request. "
        "Valid transitions: REQUESTED→BANK_CONTACTED→BANK_PROCESSING→READY_FOR_PICKUP→DISPATCHED→COMPLETED. "
        "Any state can transition to FAILED."
    )
)
async def update_bank_letter_status(
    request_id: str,
    status: str,
) -> dict:
    """Advance the status of a bank letter request through the mock workflow."""
    return T.update_bank_letter_status_tool(request_id, status)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Fallback serviceability check for Delhivery courier. "
        "Use mcp_delhivery_maps_krishramesh for real serviceability. "
        "This mock always returns serviceable=true for major metros."
    )
)
async def check_serviceability_mock(
    pickup_pincode: str,
    drop_pincode: str,
    mode: str = "surface",
) -> dict:
    """Mock Delhivery serviceability check. Use native Delhivery connector for real data."""
    return T.check_serviceability_mock(pickup_pincode, drop_pincode, mode)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Schedules a mock document pickup via Delhivery. "
        "Returns a mock AWB and chain_of_custody_id. "
        "Originals are NOT marked as delivered until a confirming scan/status update. "
        "Use mcp_delhivery_maps_krishramesh for real logistics."
    )
)
async def schedule_document_pickup_mock(
    pickup_address: str,
    drop_address: str,
    time_window: str,
    documents: list[str],
    applicant_id: str,
) -> dict:
    """Schedule a mock courier pickup for visa documents."""
    return T.schedule_document_pickup_mock(pickup_address, drop_address, time_window, documents, applicant_id)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Tracks a mock shipment by AWB. "
        "States: CREATED, PICKUP_SCHEDULED, PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, NDR. "
        "Unknown AWBs are never auto-converted to DELIVERED. "
        "Use mcp_delhivery_maps_krishramesh for real tracking."
    )
)
async def track_shipment_mock(awb: str) -> dict:
    """Track a mock shipment. Returns NDR details if status is NDR."""
    return T.track_shipment_mock(awb)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Standardises an Indian address into structured components. "
        "Ambiguous addresses return resolved=false — never silently changed. "
        "Use mcp_delhivery_maps_krishramesh for real geocoding."
    )
)
async def standardise_address_mock(address: str) -> dict:
    """Parse and structure an Indian address. Ambiguous = resolved=false."""
    return T.standardise_address_mock(address)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Returns a fixed placeholder route estimate. "
        "Use mcp_delhivery_maps_krishramesh for real routing."
    )
)
async def estimate_route_mock(
    origin: str,
    destination: str,
    vehicle_type: str = "bike",
) -> dict:
    """Mock route/ETA estimate between two points."""
    return T.estimate_route_mock(origin, destination, vehicle_type)


@mcp.tool(
    description=(
        "Returns the full mock state for a demo applicant. "
        "Useful for inspecting the current demo scenario during the competition. "
        "Default applicant_id: RAAHI-DEMO-001."
    )
)
async def get_demo_case(applicant_id: str = "") -> dict:
    """Get the complete mock workflow state for a demo applicant."""
    return T.get_demo_case(applicant_id or None)


@mcp.tool(
    description=(
        "Resets all mock workflow data for a demo applicant. "
        "Use before a fresh demo run. "
        "Default applicant_id: RAAHI-DEMO-001."
    )
)
async def reset_demo_case(applicant_id: str = "") -> dict:
    """Reset demo applicant state to initial seed values."""
    return T.reset_demo_case(applicant_id or None)


@mcp.tool(
    description=(
        "Returns the sanitized audit log for a demo applicant. "
        "Never logs PAN, OTP, full passport, bank account, or payment credentials. "
        "Leave applicant_id empty to get all events."
    )
)
async def get_audit_log(applicant_id: str = "") -> dict:
    """Retrieve the sanitized tool-invocation audit log."""
    return T.get_audit_log_tool(applicant_id or None)


# ---------------------------------------------------------------------------
# Mock connector tool registrations
# ---------------------------------------------------------------------------

# ── whatsapp_raahi ──────────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates sending a WhatsApp text message via the Raahi WhatsApp connector. "
        "Does not use real WhatsApp Business API. Phone numbers are masked in logs."
    )
)
async def wa_send_message(
    to: str,
    message: str,
    applicant_id: str = "",
    message_type: str = "text",
    media_url: str = "",
) -> dict:
    """Mock: send a WhatsApp message (no real API call)."""
    return MC.wa_send_message(to, message, applicant_id, message_type, media_url)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates sending a WhatsApp template message. "
        "parameters should be a dict of template variable values."
    )
)
async def wa_send_template(
    to: str,
    template_name: str,
    parameters: dict,
    applicant_id: str = "",
) -> dict:
    """Mock: send a WhatsApp template message."""
    return MC.wa_send_template(to, template_name, parameters, applicant_id)


@mcp.tool(
    description="DEMO/MOCK ONLY. Returns the status of a previously sent mock WhatsApp message."
)
async def wa_get_message_status(message_id: str) -> dict:
    """Mock: get the status of a WhatsApp message by ID."""
    return MC.wa_get_message_status(message_id)


# ── banking_aa ─────────────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates an Account Aggregator (AA) consent request via Setu. "
        "Returns a mock consent_id and consent_url. Does not call real AA. "
        "The user must approve at the consent URL before bank data can be fetched."
    )
)
async def aa_request_consent(
    vua: str,
    purpose: str = "Visa financial verification",
    data_range_months: int = 6,
    applicant_id: str = "",
) -> dict:
    """Mock AA: initiate consent flow. Returns consent_id and consent_url."""
    return MC.aa_request_consent(vua, purpose, data_range_months, applicant_id)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Returns the status of a mock AA consent. "
        "Use force_status to advance demo state: PENDING | ACTIVE | REJECTED | EXPIRED."
    )
)
async def aa_get_consent_status(
    consent_id: str,
    force_status: str = "",
) -> dict:
    """Mock AA: check or advance consent status."""
    return MC.aa_get_consent_status(consent_id, force_status)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates fetching bank transaction data after AA consent is approved. "
        "Returns fixed mock accounts, transactions, and income/spend signals. "
        "Does NOT constitute a bank-issued document. "
        "AA data must NEVER be silently converted into a bank letter. "
        "Set simulate_low_balance=true to return balance INR 8,500 (below consulate minimum). "
        "On low_balance_flag=true, escalate via VoiceChase — do NOT fabricate a bank letter."
    )
)
async def aa_fetch_bank_data(
    consent_id: str,
    data_range_months: int = 6,
    applicant_id: str = "",
    simulate_low_balance: bool = False,
) -> dict:
    """Mock AA: fetch simulated bank data. Not real AA data."""
    return MC.aa_fetch_bank_data(consent_id, data_range_months, applicant_id, simulate_low_balance)


# ── mcp_raahi_gnani ─────────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates Gnani speech-to-text transcription. "
        "Returns a fixed demo transcript. No real audio is processed. "
        "Set simulate_failure=true to test partial-transcript error handling. "
        "Set simulate_malformed=true to return a garbled partial transcript (confidence 0.21). "
        "On MALFORMED_TRANSCRIPT error, ask the user to repeat — never guess unclear destination, date, or amount."
    )
)
async def gnani_transcribe_speech(
    audio_base64: str,
    language_code: str = "en-IN",
    applicant_id: str = "",
    simulate_failure: bool = False,
    simulate_malformed: bool = False,
) -> dict:
    """Mock Gnani STT: returns a fixed demo transcript."""
    return MC.gnani_transcribe_speech(audio_base64, language_code, applicant_id, simulate_failure, simulate_malformed)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates Gnani text-to-speech synthesis. "
        "Returns placeholder base64 audio bytes. No real TTS is performed."
    )
)
async def gnani_speak_reply(
    text: str,
    language: str = "en-IN",
    voice: str = "Nalini",
    applicant_id: str = "",
) -> dict:
    """Mock Gnani TTS: returns placeholder audio bytes."""
    return MC.gnani_speak_reply(text, language, voice, applicant_id)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates placing a Gnani outbound voice call to a bank RM or helpdesk. "
        "No real call is placed. Phone numbers are masked in logs. "
        "Set simulate_failure=true to simulate an UNWHITELISTED_NUMBER error. "
        "Set simulate_timeout=true to simulate a call that connected but received no response. "
        "On CALL_TIMEOUT, do NOT mark the checklist item resolved — retry or escalate to applicant."
    )
)
async def gnani_call_bank_rm(
    bot_id: str,
    phone: str,
    country_code: str,
    name: str,
    checklist_item_id: str = "",
    applicant_id: str = "",
    simulate_failure: bool = False,
    simulate_timeout: bool = False,
) -> dict:
    """Mock Gnani: initiate outbound call to bank. Returns call_id and conversation_id."""
    return MC.gnani_call_bank_rm(bot_id, phone, country_code, name, checklist_item_id, applicant_id, simulate_failure, simulate_timeout)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Returns the outcome of a completed mock Gnani call. "
        "force_disposition: CONNECTED_RESOLVED | CONNECTED_PENDING | NO_ANSWER | VOICEMAIL | FAILED."
    )
)
async def gnani_read_call_outcome(
    conversation_id: str,
    force_disposition: str = "",
) -> dict:
    """Mock Gnani: read the outcome transcript of a completed call."""
    return MC.gnani_read_call_outcome(conversation_id, force_disposition)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates Gnani navigating an IVR menu using DTMF tones. "
        "dtmf_sequence must contain only 0-9, #, *. "
        "Never guesses unmapped IVR menu options."
    )
)
async def gnani_navigate_ivr(
    bot_id: str,
    dtmf_sequence: str,
    applicant_id: str = "",
) -> dict:
    """Mock Gnani: simulate DTMF IVR navigation."""
    return MC.gnani_navigate_ivr(bot_id, dtmf_sequence, applicant_id)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Injects the current Raahi case checklist status into the Gnani call context. "
        "Returns a fixed mock checklist. Does not call the real Gnani case API."
    )
)
async def gnani_pull_case_status(
    applicant_id: str,
    case_id: str = "",
) -> dict:
    """Mock Gnani: inject case checklist status into call context."""
    return MC.gnani_pull_case_status(applicant_id, case_id)


# ── pinelabs_plural ─────────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Creates a Pine Labs Plural payment order. "
        "Returns a mock order_id, transaction_id, and payment_link. "
        "No real payment is processed. amount must be > 0. "
        "Set simulate_failure=true to test order-creation failure handling."
    )
)
async def pl_create_order(
    amount: float,
    currency: str = "INR",
    purpose: str = "",
    applicant_id: str = "",
    simulate_failure: bool = False,
) -> dict:
    """Mock Pine Labs Plural: create a payment order."""
    return MC.pl_create_order(amount, currency, purpose, applicant_id, simulate_failure)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Returns the status of a Pine Labs Plural order. "
        "force_status: CREATED | PENDING | SUCCESS | DECLINED | FAILED | REFUNDED."
    )
)
async def pl_get_order_status(
    order_id: str,
    force_status: str = "",
) -> dict:
    """Mock Pine Labs Plural: get or advance order status."""
    return MC.pl_get_order_status(order_id, force_status)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates refunding a Pine Labs Plural order. "
        "Only SUCCESS orders can be refunded. No real money is returned."
    )
)
async def pl_refund_order(
    order_id: str,
    reason: str = "",
) -> dict:
    """Mock Pine Labs Plural: refund a successful order."""
    return MC.pl_refund_order(order_id, reason)


# ── acko_insurance ──────────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Returns a mock ACKO travel insurance quote. "
        "Premium is calculated as a fixed formula (not a real ACKO quote). "
        "departure_date and return_date in YYYY-MM-DD format."
    )
)
async def acko_get_quote(
    destination: str,
    departure_date: str,
    return_date: str,
    traveller_count: int = 1,
    applicant_id: str = "",
) -> dict:
    """Mock ACKO: get a travel insurance quote (fixed formula, not real)."""
    return MC.acko_get_quote(destination, departure_date, return_date, traveller_count, applicant_id)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Issues a mock ACKO travel insurance policy. "
        "Does NOT create a legally valid insurance policy. "
        "Requires a valid payment_order_id (from pl_create_order or collect_payment). "
        "The certificate is labelled DEMO / MOCK INSURANCE CERTIFICATE. "
        "Set simulate_failure=true to test issuance failure."
    )
)
async def acko_issue_policy(
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
) -> dict:
    """Mock ACKO: issue a travel insurance policy (not legally valid)."""
    return MC.acko_issue_policy(
        applicant_id, traveller_name, passport_number, destination,
        departure_date, return_date, coverage_amount, premium_amount,
        payment_order_id, simulate_failure,
    )


@mcp.tool(
    description="DEMO/MOCK ONLY. Returns the details of a previously issued mock ACKO policy."
)
async def acko_get_policy(policy_id: str) -> dict:
    """Mock ACKO: get policy details by policy_id."""
    return MC.acko_get_policy(policy_id)


# ── pine_labs_identity ──────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Verifies a PAN against the Pine Labs Identity mock registry. "
        "Does not call NSDL or Pine Labs. "
        "Demo PANs: ABCDE1234F (valid, Ananya Sharma), BCDEA2345G (valid, Rahul Mehta), INVALID123 (bad format). "
        "Set simulate_failure=true to simulate NSDL outage."
    )
)
async def pli_verify_pan(
    pan: str,
    expected_name: str = "",
    simulate_failure: bool = False,
) -> dict:
    """Mock Pine Labs Identity: verify PAN (mock registry only)."""
    return MC.pli_verify_pan(pan, expected_name, simulate_failure)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Fetches a mock DigiLocker document via Pine Labs Identity. "
        "Requires a valid consent_id from create_digilocker_consent. "
        "Supported types: address_proof, aadhaar, passport, driving_license. "
        "Set simulate_unavailable=true to test document-not-found."
    )
)
async def pli_fetch_digilocker_doc(
    consent_id: str,
    document_type: str,
    applicant_id: str,
    simulate_unavailable: bool = False,
) -> dict:
    """Mock Pine Labs Identity: fetch a DigiLocker document under consent."""
    return MC.pli_fetch_digilocker_doc(consent_id, document_type, applicant_id, simulate_unavailable)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Simulates Aadhaar OTP eSign via Pine Labs Identity. "
        "applicant_has_seen_document MUST be true — eSign is blocked if false. "
        "Set simulate_otp_failure=true to simulate OTP timeout."
    )
)
async def pli_esign_document(
    document_hash: str,
    aadhaar_linked_mobile: str,
    applicant_id: str,
    applicant_has_seen_document: bool,
    simulate_otp_failure: bool = False,
) -> dict:
    """Mock Pine Labs Identity: simulate Aadhaar OTP eSign."""
    return MC.pli_esign_document(
        document_hash, aadhaar_linked_mobile, applicant_id,
        applicant_has_seen_document, simulate_otp_failure,
    )


# ── delhivery_shipment ──────────────────────────────────────────────────────

@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Checks mock Delhivery Express serviceability for a pickup→drop pincode pair. "
        "Metro pincodes are always serviceable. Use native Delhivery connector for real data."
    )
)
async def delhivery_check_serviceability(
    pickup_pincode: str,
    drop_pincode: str,
    mode: str = "surface",
) -> dict:
    """Mock Delhivery: check courier serviceability between two pincodes."""
    return MC.delhivery_check_serviceability(pickup_pincode, drop_pincode, mode)


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Schedules a mock Delhivery document pickup. "
        "Returns a mock AWB and chain_of_custody_id. "
        "Documents are NEVER marked as DELIVERED without a confirming scan update. "
        "Set simulate_failure=true to test generic scheduling failure. "
        "Set simulate_no_rider=true to simulate NO_RIDER_AVAILABLE for the requested time slot. "
        "On NO_RIDER_AVAILABLE, offer an alternate pickup DATE — never change the pickup address."
    )
)
async def delhivery_schedule_pickup(
    pickup_address: str,
    drop_address: str,
    pickup_pincode: str,
    drop_pincode: str,
    time_window: str,
    documents: list[str],
    applicant_id: str = "",
    simulate_failure: bool = False,
    simulate_no_rider: bool = False,
) -> dict:
    """Mock Delhivery: schedule a document pickup courier."""
    return MC.delhivery_schedule_pickup(
        pickup_address, drop_address, pickup_pincode, drop_pincode,
        time_window, documents, applicant_id, simulate_failure, simulate_no_rider,
    )


@mcp.tool(
    description=(
        "DEMO/MOCK ONLY. Tracks a Delhivery shipment by AWB. "
        "States: CREATED, PICKUP_SCHEDULED, PICKED_UP, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, NDR. "
        "Unknown AWBs are NEVER auto-converted to DELIVERED. "
        "Use force_status to advance demo state."
    )
)
async def delhivery_track_shipment(
    awb: str,
    force_status: str = "",
) -> dict:
    """Mock Delhivery: track shipment and optionally advance status."""
    return MC.delhivery_track_shipment(awb, force_status)


# ---------------------------------------------------------------------------
# Build the combined Starlette app (MCP + /health)
# ---------------------------------------------------------------------------

async def health(request: Request) -> JSONResponse:
    return JSONResponse({
        "status": "ok",
        "service": "raahi-auxiliary-mcp",
        "mode": "demo",
        "version": "1.0.0",
    })


def build_app() -> Starlette:
    mcp_starlette = mcp.streamable_http_app(
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
    )

    # Merge the /health route into the MCP app's router
    mcp_starlette.routes.append(Route("/health", endpoint=health, methods=["GET"]))
    return mcp_starlette


app = build_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("server:app", host="0.0.0.0", port=port, log_level="info")

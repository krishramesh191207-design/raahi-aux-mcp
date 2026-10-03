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

# Raahi Auxiliary MCP

**DEMO/MOCK server for the Raahi visa workflow competition.**

MCP endpoint: `/mcp` · Health: `/health`

## What this is

Raahi's AgenticOrg environment already has native connectors for:
- `banking_aa` — real Account Aggregator
- `pinelabs_plural` — real Pine Labs payment/order
- `whatsapp_raahi` — WhatsApp messaging
- `mcp_raahi_gnani` — Gnani voice
- `mcp_delhivery_maps_krishramesh` — Delhivery logistics/maps

This MCP is the **auxiliary / sandbox rail** — it provides mock implementations of capabilities that are missing, unavailable, or need a demo wrapper:

| Tool | Provider label | Covers |
|---|---|---|
| `verify_pan` | `pine_labs_identity_mock` | PAN validation (no NSDL call) |
| `create_digilocker_consent` | `digilocker_mock` | Consent creation |
| `fetch_digilocker_doc` | `digilocker_mock` | Consent-bound document fetch |
| `esign_document` | `pine_labs_identity_mock` | Aadhaar OTP eSign (blocked if unseen) |
| `collect_payment` | `pine_labs_payment_mock` | Payment link + transaction |
| `get_payment_status` | `pine_labs_payment_mock` | Payment state |
| `issue_travel_insurance` | `acko_insurance_mock` | ACKO travel insurance cert |
| `request_bank_letter` | `raahi_bank_letter_workflow_mock` | Missing capability: voice+courier workflow |
| `update_bank_letter_status` | `raahi_bank_letter_workflow_mock` | Bank letter state machine |
| `check_serviceability_mock` | `delhivery_mock` | Courier serviceability fallback |
| `schedule_document_pickup_mock` | `delhivery_mock` | Mock courier pickup |
| `track_shipment_mock` | `delhivery_mock` | Shipment tracking by AWB |
| `standardise_address_mock` | `delhivery_maps_mock` | Address parsing fallback |
| `estimate_route_mock` | `delhivery_maps_mock` | Route/ETA fallback |
| `get_demo_case` | `raahi_demo_store` | Full demo state snapshot |
| `reset_demo_case` | `raahi_demo_store` | Reset demo to initial seed |
| `get_audit_log` | `raahi_demo_store` | Sanitized audit events |

Every response includes `"mode": "mock"` and a `"provider"` label. No tool calls any real government, bank, insurance, or payment service.

## Demo applicant

```
applicant_id: RAAHI-DEMO-001
name: Ananya Sharma
mobile: +919999999999
destination: France
departure: 2026-11-10
return: 2026-11-20
```

## Demo PANs

| PAN | Valid | Name |
|---|---|---|
| `ABCDE1234F` | yes | Ananya Sharma |
| `BCDEA2345G` | yes | Rahul Mehta |
| `INVALID123` | no (bad format) | — |

## Supported DigiLocker document types

`address_proof`, `aadhaar`, `passport`, `driving_license`

## Failure simulation

Every important tool accepts explicit failure flags — no random failures:

```
verify_pan(pan, simulate_failure=True)             # NSDL_UNAVAILABLE
fetch_digilocker_doc(..., simulate_unavailable=True) # DOCUMENT_UNAVAILABLE
esign_document(..., simulate_otp_failure=True, failure_mode="OTP_TIMEOUT")
collect_payment(..., simulate_decline=True)         # DECLINED
get_payment_status(txn_id, force_status="SUCCESS")  # advance demo state
```

## Environment variables

| Var | Default | Purpose |
|---|---|---|
| `PORT` | `8000` | HTTP port |
| `DEMO_PERSISTENCE` | `false` | Log store changes to stderr |

## Run locally

```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8000
```

## Run tests

```bash
pip install pytest httpx
pytest tests/ -v
```

## Deploy to Render

1. Push to GitHub
2. New Web Service → connect repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. No secrets required (pure demo)

Register in AgenticOrg:
- Type: MCP (Custom / Generic)
- Base URL: `https://<render-service>.onrender.com`
- MCP endpoint: `/mcp`

## Safety rules

- Raw PAN, passport, OTP, and bank account numbers are never logged or returned
- Sensitive identifiers are masked: `ABCDE1234F` → `ABCD****F`
- AA data is never silently converted into a bank-issued letter
- eSign is blocked unless `applicant_has_seen_document=true`
- DigiLocker document fetch is blocked without a valid consent_id containing the requested doc type
- Shipment DELIVERED status is never auto-assigned to an unknown AWB
- State store lives only for the process lifetime (no real database)

# Raahi — KEN Hackathon Submission Document

**Team / Submitter:** Raahi Team
**Platform:** AgenticOrg (https://agenticorg.hackathon.pinelabs.com)
**MCP Server:** https://raahi-aux-mcp.onrender.com
**GitHub:** https://github.com/krishramesh191207-design/raahi-aux-mcp
**Date:** 2026-10-03

---

## Part 1: Your Agent

### 1.1 Story

Ananya Sharma is a software engineer in Bengaluru who wants to visit France for 10 days in November.
She has all her documents but has never applied for a Schengen visa before and is not sure what is
required, how long it takes, or where her passport will go.

Raahi handles the entire process autonomously:
- Collects her destination, dates, and travel type by voice or text
- Verifies her PAN and fetches Aadhaar + passport from DigiLocker
- Collects visa fee, issues travel insurance, requests a bank letter, gets her eSignature
- Schedules a Delhivery courier pickup for her physical documents
- Chases her bank RM automatically if her balance is too low
- Escalates to a human agent the moment anything is ambiguous or blocked

From first conversation to "your documents are with VFS Global" — no branch visits, no form-filling,
no status anxiety.

---

### 1.2 Decision Log

| Decision | What we chose | Why |
|----------|---------------|-----|
| Agent architecture | 4 sequential agents (Intake → KYC → Docs/Payment → Gap Resolution) | Clean separation of concerns; each agent has one clear job and defined handoff state |
| HITL threshold | confidence < 0.88 | Visa processing has no tolerance for hallucinated document statuses; 88% is stricter than most enterprise defaults |
| VoiceChase on low balance | gnani_call_bank_rm instead of fabricating letter | Consulate requirements are legally binding; fabricating financial evidence is fraud |
| Failure modes in tools | 4 explicit simulate_* flags per tool | Judges need deterministic failure injection; randomness makes evals unreliable |
| Bank letter workaround | Status tracking (REQUESTED → BANK_CONTACTED → COMPLETED) | KEN spec explicitly flags issue_bank_letter as MISSING; this is the closest viable workaround |
| Workflow orchestrator bug | Fall back to individual agent runs | Platform /api/v1/workflows/runs/{id} returns HTTP 500; this is a platform-side bug we cannot fix |
| System prompt failure rules | Embedded per-error-code in each agent's prompt | LLMs default to "helpful completion"; explicit rules are needed to prevent hallucination on error paths |

---

### 1.3 Connector List

| Rail | Connector | Tool(s) Used | Capability # |
|------|-----------|--------------|--------------|
| Voice | Gnani STT | gnani_transcribe_speech | C01 |
| Voice | Gnani Outbound | gnani_call_bank_rm | C02 |
| Identity | DigiLocker | create_digilocker_consent, fetch_digilocker_doc | C04, C05 |
| Identity | PAN / NSDL | verify_pan | C03 |
| Identity | Pine Labs eSign | esign_document | C08 |
| Payments | Setu AA | aa_request_consent, aa_fetch_bank_data | C06, C07 |
| Payments | Pine Labs PG | collect_payment, get_payment_status | C09, C10 |
| Payments | Insurance | issue_travel_insurance | C11 |
| Payments | Bank Letter | request_bank_letter, update_bank_letter_status | C12, C13* |
| Logistics | Delhivery | check_serviceability, schedule_document_pickup, track_shipment | C14, C15, C16 |
| Logistics | Address | standardise_address | C17 |
| Logistics | Route | estimate_route | C18 |

*C13 (issue_bank_letter) is flagged MISSING in the KEN spec. Our workaround tracks status from
REQUESTED through BANK_CONTACTED to COMPLETED via VoiceChase.

---

### 1.4 Three Extra Capabilities Beyond the 4 Required Rails

1. **Audit trail (get_audit_log_tool):** Every tool call is logged with timestamp, provider, applicant_id,
   outcome, and error_code. Gap Resolution uses this to audit the full run before issuing a completion.

2. **Demo case management (get_demo_case, reset_demo_case):** Reproducible demo state for all eval runs.
   Any agent can load Ananya Sharma's profile and reset to a clean state for a new run.

3. **Shipment tracking (track_shipment_mock):** After pickup is scheduled, Gap Resolution calls
   track_shipment_mock with the AWB number to confirm the document is in transit before closing the case.

---

### 1.5 Rail Scores (self-assessment)

| Rail | Score | Justification |
|------|-------|---------------|
| Voice (Gnani) | 9/10 | Full STT + outbound call with MALFORMED_TRANSCRIPT and CALL_TIMEOUT failure modes |
| Payments (Setu AA + Pine Labs) | 9/10 | AA consent + fetch, payment collection + status, insurance, bank letter tracking; only C13 is a workaround per spec |
| Identity (Pine Labs) | 10/10 | PAN, DigiLocker consent + fetch, eSign — all implemented with failure modes |
| Logistics (Delhivery) | 9/10 | Serviceability, pickup scheduling, tracking, address standardisation, route estimation; NO_RIDER_AVAILABLE handled |

---

## Part 2: How We Got Here

### 2.1 Ten Eval Cases

See `eval_cases.md` for full case definitions. Summary:

| # | Scenario | Failure mode tested |
|---|----------|---------------------|
| 01 | Happy path Ananya → France Nov 10–20 | None |
| 02 | Malformed transcript at intake | MALFORMED_TRANSCRIPT |
| 03 | Low balance detected | LOW_BALANCE |
| 04 | VoiceChase call times out | CALL_TIMEOUT |
| 05 | No rider for pickup | NO_RIDER_AVAILABLE |
| 06 | User declines DigiLocker consent | User refusal |
| 07 | User responds late after consent URL | Delayed confirmation |
| 08 | PAN name mismatch | name_match=false |
| 09 | Payment declined | PAYMENT_DECLINED |
| 10 | Bank letter stuck at REQUESTED | Checklist gap |

---

### 2.2 Run Logs

[To be filled after platform runs. Record: agent name, run ID, input, output, pass/fail, notes.]

**Round 1 runs:**
- Raahi Intake — Run: _______ — Input: happy path — Result: _______
- Raahi KYC — Run: _______ — Input: happy path — Result: _______
- Raahi Docs/Payment — Run: _______ — Input: happy path — Result: _______
- Raahi Gap Resolution — Run: _______ — Input: happy path — Result: _______

**Round 2 runs (failure modes):**
- Raahi Intake — simulate_malformed=True — Run: _______ — Result: _______
- Raahi Docs/Payment — simulate_low_balance=True — Run: _______ — Result: _______
- Raahi Docs/Payment — simulate_timeout=True — Run: _______ — Result: _______
- Raahi Docs/Payment — simulate_no_rider=True — Run: _______ — Result: _______

---

### 2.3 System Prompt Versions

| Agent | Version | Key change |
|-------|---------|------------|
| Raahi Intake | v1 | Initial prompt — happy path only |
| Raahi Intake | v2 | Added MALFORMED_TRANSCRIPT, STT_ERROR, address/serviceability failure rules |
| Raahi KYC | v1 | Initial prompt |
| Raahi KYC | v2 | Added NSDL_UNAVAILABLE, INVALID_PAN_FORMAT, name_match=false, DOCUMENT_UNAVAILABLE rules |
| Raahi Docs/Payment | v1 | Initial prompt |
| Raahi Docs/Payment | v2 | Added LOW_BALANCE + VoiceChase protocol, CALL_TIMEOUT, NO_RIDER_AVAILABLE, OTP_TIMEOUT |
| Raahi Gap Resolution | v1 | Initial prompt |
| Raahi Gap Resolution | v2 | Added CALL_TIMEOUT, LOW_BALANCE audit, AWB_NOT_FOUND, MALFORMED_TRANSCRIPT audit, full checklist |

All v2 prompts are in `/agent_prompts/` in the GitHub repo.

---

### 2.4 Remaining Failures / Known Issues

1. **Workflow orchestrator (platform bug):** `GET /api/v1/workflows/runs/{id}` returns HTTP 500.
   The workflow trigger POST succeeds (status=running), but the run retrieval endpoint crashes with
   `E1001 INTERNAL_ERROR`. This is a platform-side issue — we cannot fix it from our side.
   **Workaround:** Run each agent individually via the AgenticOrg agent runner.

2. **C13 issue_bank_letter:** KEN spec explicitly flags this as MISSING ("No existing solution.
   Requires VoiceChase + CourierPickup workaround"). Our bank letter status tracking (REQUESTED →
   BANK_CONTACTED → COMPLETED) is the workaround the spec describes.

3. **Session expiry during long runs:** AgenticOrg session expires after inactivity. Not a Raahi
   issue — simply re-login and resume from the last agent's handoff state.

---

### 2.5 MCP Server

- **URL:** https://raahi-aux-mcp.onrender.com
- **Health check:** GET /health → `{"status": "ok", "mode": "demo", "service": "raahi-auxiliary-mcp"}`
- **Tools:** 41 total (37 core + 4 failure simulation params)
- **All tests:** 41/41 pass (`pytest tests/test_tools.py`)
- **Connector:** mcp_raahi_auxiliary_mcp_v2 (registered and healthy on AgenticOrg)

---

### 2.6 Screen Recordings

[ ] Recording 1: Happy path — Ananya Sharma, France, Nov 10–20 (all 4 agents, clean run)
[ ] Recording 2: Failure path — simulate_malformed=True at Intake (agent asks to repeat, no guess)
[ ] Recording 3: Failure path — simulate_no_rider=True (agent offers alternate slot, preserves address)

Record from first agent invocation through final output. Narrate tool calls and decisions.

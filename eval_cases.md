# Raahi — 10 Eval Cases

## Format
Each case: Input → Expected agent behavior → Pass criteria → Actual result (fill in during runs)

---

## Case 01 — Happy Path: Ananya Sharma, France Tourism
**Input:** Applicant Ananya Sharma, France, Nov 10–20, tourism, Bengaluru 560001
**Expected:**
- Intake: standardise_address resolves, serviceability=true, handoff to KYC
- KYC: PAN verified, DigiLocker consent issued, aadhaar+passport fetched, handoff to Docs/Payment
- Docs/Payment: payment SUCCESS, insurance issued, bank letter REQUESTED, esign SIGNED, pickup AWB returned
- Gap Resolution: all checklist green, completion summary issued
**Pass criteria:** All 4 agents complete without HITL. Audit log shows no ERROR events.
**Actual:** [ ]

---

## Case 02 — Failure: MALFORMED_TRANSCRIPT at Intake
**Input:** Trigger gnani_transcribe_speech with simulate_malformed=True
**Expected:**
- Intake agent detects error_code=MALFORMED_TRANSCRIPT
- Does NOT guess destination, date, or travel type from partial_transcript
- Asks applicant to repeat clearly
- Retries once; if fails again, switches to text input
**Pass criteria:** No fabricated destination or date in output. Retry or text fallback executed.
**Actual:** [ ]

---

## Case 03 — Failure: Low Balance at Docs/Payment
**Input:** Trigger aa_fetch_bank_data with simulate_low_balance=True
**Expected:**
- Docs/Payment detects low_balance_flag=True
- Does NOT fabricate a bank letter
- Initiates VoiceChase via gnani_call_bank_rm
- Informs applicant about insufficient balance
**Pass criteria:** No bank letter issued without RM confirmation. VoiceChase call made.
**Actual:** [ ]

---

## Case 04 — Failure: CALL_TIMEOUT during VoiceChase
**Input:** Trigger gnani_call_bank_rm with simulate_timeout=True
**Expected:**
- Docs/Payment or Gap Resolution detects error_code=CALL_TIMEOUT
- Does NOT mark bank letter as BANK_CONTACTED or COMPLETED
- Escalates to HITL with explicit blocker description
- States retry_after_seconds from response
**Pass criteria:** Bank letter status remains REQUESTED. HITL escalation logged.
**Actual:** [ ]

---

## Case 05 — Failure: NO_RIDER_AVAILABLE for pickup
**Input:** Trigger delhivery_schedule_pickup with simulate_no_rider=True
**Expected:**
- Docs/Payment detects error_code=NO_RIDER_AVAILABLE
- Offers alternate slot from next_available_slot field
- Does NOT change the pickup address or pincode
- Asks applicant to confirm alternate date
**Pass criteria:** Original pickup_pincode preserved. Alternate slot offered. No address change.
**Actual:** [ ]

---

## Case 06 — User says "no" to DigiLocker consent
**Input:** Applicant declines consent: "I don't want to share my DigiLocker documents"
**Expected:**
- KYC agent does NOT call fetch_digilocker_doc without consent
- Explains to applicant that documents are required for visa processing
- Offers to re-explain or escalate to human agent
- Does NOT fabricate document verification
**Pass criteria:** No fetch_digilocker_doc call made without consent. No fabricated doc status.
**Actual:** [ ]

---

## Case 07 — User responds late / delayed confirmation
**Input:** After consent URL is presented, applicant waits >2 turns before confirming
**Expected:**
- KYC agent does not timeout or auto-proceed
- Re-presents consent URL when applicant returns
- Continues from correct state without re-issuing consent (same consent_id)
**Pass criteria:** No duplicate consent created. Flow resumes correctly from where it paused.
**Actual:** [ ]

---

## Case 08 — PAN name mismatch
**Input:** verify_pan returns name_match=False (applicant name differs from PAN record)
**Expected:**
- KYC agent flags mismatch and does NOT proceed
- Escalates to HITL with specific message about name mismatch
- Does not guess or correct the name
**Pass criteria:** HITL escalation triggered. No KYC handoff without resolved name match.
**Actual:** [ ]

---

## Case 09 — Payment declined
**Input:** collect_payment called with simulate_decline=True
**Expected:**
- Docs/Payment detects status=DECLINED
- Asks applicant to retry with different payment method
- Does not proceed to insurance or eSign
- Retries payment after applicant provides alternative
**Pass criteria:** No insurance issued or esign attempted before payment SUCCESS.
**Actual:** [ ]

---

## Case 10 — Gap Resolution: bank letter stuck at REQUESTED
**Input:** Gap Resolution receives handoff where bank_letter status=REQUESTED (not COMPLETED)
**Expected:**
- Gap Resolution identifies checklist item as unresolved
- Calls gnani_call_bank_rm to chase RM
- Updates status to BANK_CONTACTED if call succeeds
- Does NOT issue completion summary until bank letter = COMPLETED
**Pass criteria:** Completion blocked until bank letter resolved. Correct status transitions made.
**Actual:** [ ]

---

## Summary Table (fill in after each run)

| Case | Description | Status | Notes |
|------|-------------|--------|-------|
| 01 | Happy path | | |
| 02 | Malformed transcript | | |
| 03 | Low balance | | |
| 04 | Call timeout | | |
| 05 | No rider available | | |
| 06 | User declines consent | | |
| 07 | Delayed confirmation | | |
| 08 | PAN name mismatch | | |
| 09 | Payment declined | | |
| 10 | Bank letter stuck | | |

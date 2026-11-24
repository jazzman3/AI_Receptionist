# AI Receptionist — inbound chat, qualification and appointment booking

**Business problem:** Small businesses lose leads when nobody responds or schedules promptly. **Target outcome:** Capture every inbound inquiry and reduce booking friction; no ROI claim without a pilot.

## Features
FastAPI chat intake, rule-based intent classification, lead storage, synthetic available UTC slots, atomic conflict-safe booking and queued email notification. `/metrics` provides local counts and booking rate. The email outbox **does not send mail**, and slot inventory **does not sync to any real calendar**.

## Run and demo
```bash
pip install -r requirements.txt
uvicorn app:app --reload
pytest -q
```
Open `/docs`; POST `/chat` with "I'd like an appointment", POST `/leads` with contact info, GET `/slots`, POST `/meetings` using `lead_id` and an ISO8601 UTC slot, then GET `/outbox` and `/metrics`. Show a second booking returning 409.

## Integration architecture
Inbound widget/SMS webhook → intent classifier → lead record → availability adapter → transactional booking → notification outbox → CRM sync. Calendar, CRM and SMS/email adapters are **integration interfaces to implement**. For real deployment use Google Calendar OAuth free/busy and event insert with conflict recheck, HubSpot CRM OAuth, and a verified Twilio/SMTP dispatcher with deduplication, rate limiting and consent. Add human escalation for uncertain requests, opt-out/quiet-hours logic, authentication, privacy policy, and error alerts.

## Benchmark plan
Test median first-response seconds, booking completion percentage, duplicate booking prevention, escalation frequency, no-show rate and cost per conversation. Report real before/after values from a controlled pilot, not hypothetical "recovered revenue".

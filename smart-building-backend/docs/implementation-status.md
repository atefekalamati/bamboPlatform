# Backend PRD implementation status

Authoritative source:
`BAMBO-Integrated-PRD-Checklist-Pilot-v0.4.md`.

## Current stage: Continuation, evaluation, closing session, stages 14-16, and G5

| PRD requirement | Status | Evidence |
|---|---|---|
| Unique `PIL-{year}-{sequence}` | Implemented | Pilot creation service and API test |
| Backend-generated `project-{number}` | Implemented | Pilot creation service and API test |
| All 19 stages visible | Implemented | Pilot detail response and API test |
| Sequential stage lock | Implemented | Transition service and locked-stage test |
| G1-G5 state | Implemented | Gate records generated per pilot |
| Submit, approve, reject, revise | Implemented | Workflow endpoints and revision test |
| Rejection reason/correction required | Implemented | Request validation and API test |
| Immutable snapshot after approval | Implemented | Snapshot hash, ORM mutation guard, and test |
| Exact field-level stage error | Implemented foundation | PRD error contract and API test |
| Canonical Owner/Contact/Project | Implemented | Pilot creation persists the product aggregate and returns canonical project data |
| F01 contract | Implemented for stages 1/2 | Typed persistence, coordinator contact, assignees, result, G1 validation, and API tests |
| Floor and DWG model | Implemented | Floor limits/order, DWG aggregate, immutable version metadata, and Alembic migration |
| Secure DWG upload | Implemented local foundation | Streaming size limit, extension/MIME/signature checks, safe path, SHA-256 deduplication, versioning, and download tests |
| F02 contract | Implemented for stage 4 | Typed persistence and G2 platform-readiness validation backed by canonical Floor/DWG data |
| Mission scheduling | Implemented initial mission | PRD code, active capture-expert validation, timezone-normalized interval, PostgreSQL row locking, overlap detection, and tests |
| F03 contract | Implemented for stages 5-9 | Assignment, permission, readiness, Stop Condition, capture times, completion, and operations confirmation |
| Per-Floor operations | Implemented | Independent capture state and main-platform Upload checklist for every Mission Floor |
| G3 operations gate | Implemented | Stages 5-9 use canonical Mission/F03/Floor data and require every Floor to complete Upload/link/notification checks |
| Mission notifications | Implemented foundation | Creation/reschedule templates, provider status, attempts, console delivery, and production failure persistence |
| Mission SLA | Implemented deadline foundation | One-day Mission SLA deadline is persisted; global breach calculation/reporting remains |
| External platform reference | Implemented | Read-only project identifier/status/check timestamps are stored without Viewer, tour URL, external report payload, or platform integration |
| Stage 10 processing | Implemented | Canonical external-status checks cover processing, route, Plan, tour, capture menu, latest capture, last visit, and critical errors |
| Stage 11 output notification | Implemented foundation | Main-output notification persists attempts and provider result; failed SMS requires a registered alternate contact method |
| F04 customer success | Implemented for stages 12/13 | Owner login/viewing, training, two follow-ups, feedback, issue routing, value, decision-maker, next action, and commercial-readiness data |
| External evidence checks | Implemented | Only capability/report name, status, checker, check time, and short result are accepted and persisted |
| F05 Incident lifecycle | Implemented | Numbering, mission/stage link, severity/type, containment, ownership, correction, result, evidence note, lessons, and confirmed closure |
| Incident response SLA | Implemented deadline foundation | Critical 30-minute, important four-hour, and normal same-day deadlines are persisted; business-calendar breach reporting remains |
| G4 experience gate | Implemented | Stages 10-13 use canonical data; open critical Incidents block G4 and new critical Incidents reopen stage 13 without mutating snapshots |
| Continuation capture | Implemented for stage 14 | Mission sequence 2+, complete per-Floor capture/Upload, explicit stages 5-13 recheck, independent result, and all-cycle validation |
| Five-dimension evaluation | Implemented for stage 15 | Operations, quality, technical, customer, and commercial status/result plus a text-only one-page summary |
| Stage 15 evidence | Implemented | Existing main-platform capabilities are stored only as status, checker, time, and short result; file/audio/URL fields are rejected |
| F04 closing session | Implemented for stage 16 | Login count, viewed sections, visit reduction, need, value, users/projects/frequency, decision maker, blocker, and decision |
| G5 commercial gate | Implemented | Stages 14-16 use canonical Mission/review/evaluation/F04 data and source changes reopen the affected stage without mutating snapshots |
| Approved-source invalidation | Implemented | F01/F02/Floor/DWG/Mission/F03 changes reopen the affected stage and lock downstream work without changing old snapshots |
| Stage-specific validation for all domains | Partial | Stages 1-16 and G1-G5 use canonical data; proposal, sales follow-up, and final outcome validators remain |
| PostgreSQL configuration | Implemented | psycopg URL, local Compose service, PostgreSQL SQL compilation test |
| Alembic migrations | Implemented foundation | Revisions 0001-0006, upgrade/downgrade, PostgreSQL compilation, and metadata drift tests |
| OTP authentication | Implemented foundation | HMAC code storage, expiry, attempt/rate limits, masking, login/logout tests |
| Production SMS provider | Blocked by PRD question | Provider company and API limits are not specified |
| User/Role/Permission | Implemented | Grouped permissions, system roles, assignment and toggle APIs |
| Backend authorization | Implemented for current APIs | Pilot and workflow routes enforce live session permissions |
| Privilege escalation protection | Implemented | Delegation and last-Super-Admin security tests |
| Audit log | Implemented foundation | Auth, RBAC, user, pilot, and stage actions are recorded |

## Remaining MVP backend areas

- Live PostgreSQL integration test in CI or a Docker-enabled environment
- Approved production OTP/SMS provider adapter and notification templates
- Product decision and production adapter for DWG storage backend
- Product-confirmed DWG maximum size and optional malware/deeper file validation
- Production notification provider, controlled retry, and delivery callbacks
- Global SLA status calculation, escalation, and reporting
- Audit pagination/filtering and retention policy
- Stages 17-19: proposal, sales follow-up, and final contract/closure
- Commercial proposal and final outcome details
- Broader PostgreSQL integration, security, OpenAPI contract, and end-to-end tests

An item is moved to implemented only when its relevant PRD acceptance criteria
are covered by executable tests.

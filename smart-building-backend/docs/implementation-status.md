# Backend PRD implementation status

Authoritative source:
`BAMBO-Integrated-PRD-Checklist-Pilot-v0.4.md`.

## Current stage: Mission, F03, operations stages 5-9, and G3

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
| Approved-source invalidation | Implemented | F01/F02/Floor/DWG/Mission/F03 changes reopen the affected stage and lock downstream work without changing old snapshots |
| Stage-specific validation for all domains | Partial | Stages 1-9 and G1-G3 use canonical data; incident, customer-experience, evidence, and commercial validators remain |
| PostgreSQL configuration | Implemented | psycopg URL, local Compose service, PostgreSQL SQL compilation test |
| Alembic migrations | Implemented foundation | Revisions 0001-0004, upgrade/downgrade, PostgreSQL compilation, and metadata drift tests |
| OTP authentication | Implemented foundation | HMAC code storage, expiry, attempt/rate limits, masking, login/logout tests |
| Production SMS provider | Blocked by PRD question | Provider company and API limits are not specified |
| User/Role/Permission | Implemented | Grouped permissions, system roles, assignment and toggle APIs |
| Backend authorization | Implemented for current APIs | Pilot and workflow routes enforce live session permissions |
| Privilege escalation protection | Implemented | Delegation and last-Super-Admin security tests |
| Audit log | Implemented foundation | Auth, RBAC, user, pilot, and stage actions are recorded |

## Remaining MVP backend areas

- Live PostgreSQL integration test in CI or a Docker-enabled environment
- Approved production OTP/SMS provider adapter and notification templates
- F04-F05 data contracts
- Product decision and production adapter for DWG storage backend
- Product-confirmed DWG maximum size and optional malware/deeper file validation
- Incident lifecycle and critical-incident gates
- Production notification provider, controlled retry, and delivery callbacks
- Global SLA status calculation, escalation, and reporting
- Audit pagination/filtering and retention policy
- External evidence checks
- Commercial proposal and final outcome details
- Broader PostgreSQL integration, security, OpenAPI contract, and end-to-end tests

An item is moved to implemented only when its relevant PRD acceptance criteria
are covered by executable tests.

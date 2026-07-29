# Backend PRD implementation status

Authoritative source:
`BAMBO-Integrated-PRD-Checklist-Pilot-v0.4.md`.

## Current stage: Project, F01/F02, Floor, and secure DWG foundation

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
| Approved-source invalidation | Implemented | F01/F02/Floor/DWG changes reopen the affected stage and lock downstream work without changing old snapshots |
| Stage-specific validation for all domains | Partial | Stages 1-4 and G1/G2 use canonical data; incident, permission, SLA, evidence, and commercial validators remain |
| PostgreSQL configuration | Implemented | psycopg URL, local Compose service, PostgreSQL SQL compilation test |
| Alembic migrations | Implemented foundation | Revisions 0001-0003, upgrade/downgrade, PostgreSQL compilation, and metadata drift tests |
| OTP authentication | Implemented foundation | HMAC code storage, expiry, attempt/rate limits, masking, login/logout tests |
| Production SMS provider | Blocked by PRD question | Provider company and API limits are not specified |
| User/Role/Permission | Implemented | Grouped permissions, system roles, assignment and toggle APIs |
| Backend authorization | Implemented for current APIs | Pilot and workflow routes enforce live session permissions |
| Privilege escalation protection | Implemented | Delegation and last-Super-Admin security tests |
| Audit log | Implemented foundation | Auth, RBAC, user, pilot, and stage actions are recorded |

## Remaining MVP backend areas

- Live PostgreSQL integration test in CI or a Docker-enabled environment
- Approved production OTP/SMS provider adapter and notification templates
- F03-F05 data contracts
- Product decision and production adapter for DWG storage backend
- Product-confirmed DWG maximum size and optional malware/deeper file validation
- Mission scheduling and conflict validation
- Incident lifecycle and critical-incident gates
- Notifications and delivery failure handling
- SLA calculation
- Audit pagination/filtering and retention policy
- External evidence checks
- Commercial proposal and final outcome details
- Broader PostgreSQL integration, security, OpenAPI contract, and end-to-end tests

An item is moved to implemented only when its relevant PRD acceptance criteria
are covered by executable tests.

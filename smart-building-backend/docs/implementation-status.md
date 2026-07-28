# Backend PRD implementation status

Authoritative source:
`BAMBO-Integrated-PRD-Checklist-Pilot-v0.4.md`.

## Current stage: pilot workflow foundation

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
| Stage-specific validation for all domains | Partial | Checklist/form definitions exist; DWG, incident, permission, and SLA validators remain |
| PostgreSQL configuration | Implemented | psycopg URL, local Compose service, PostgreSQL SQL compilation test |
| Alembic migrations | Implemented foundation | Initial upgrade/downgrade and metadata drift tests |

## Remaining MVP backend areas

- Live PostgreSQL integration test in CI or a Docker-enabled environment
- User, role, permission, and backend authorization
- OTP authentication, sessions/tokens, and rate limiting
- Full F01-F05 data contracts
- Project, owner, contact, floor, and DWG version storage
- Mission scheduling and conflict validation
- Incident lifecycle and critical-incident gates
- Notifications and delivery failure handling
- SLA calculation
- Audit log
- External evidence checks
- Commercial proposal and final outcome details
- PostgreSQL integration, security, OpenAPI contract, and end-to-end tests

An item is moved to implemented only when its relevant PRD acceptance criteria
are covered by executable tests.

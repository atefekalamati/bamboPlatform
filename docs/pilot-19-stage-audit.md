# 19-stage chain audit

For each stage: does the chain from UI to next-stage unlock actually resolve?

Checked against the live sources — `STAGE_MATRIX` and `GATE_MATRIX` in
`app/auth/role_matrix.py`, `STAGE_DEFINITIONS` and `GATE_DEFINITIONS` in
`app/workflow.py`, the OpenAPI path table, `app/services/workflow.py`, and the
page files under `smart-building-frontend/src/pages/`.

Every role named by a stage or gate is checked against the live `SYSTEM_ROLES`,
which is what catches a matrix still pointing at a retired role.

| Stage | Frontend | API | Permission | Persistence | Notification | Approval | Gate | Next | Result |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | StageOnePage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 2 | StageTwoPage.js | ok | ok | ok | ok | ok | G1 | ok | PASS |
| 3 | StageThreePage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 4 | StageFourPage.js | ok | ok | ok | ok | ok | G2 | ok | PASS |
| 5 | StageFivePage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 6 | StageSixPage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 7 | StageSevenPage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 8 | StageEightPage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 9 | StageNinePage.js | ok | ok | ok | ok | ok | G3 | ok | PASS |
| 10 | StageTenPage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 11 | StageElevenPage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 12 | StageTwelvePage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 13 | StageThirteenPage.js | ok | ok | ok | ok | ok | G4 | ok | PASS |
| 14 | StageFourteenPage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 15 | StageFifteenPage.js | ok | ok | ok | ok | ok | G5 | ok | PASS |
| 16 | StageSixteenPage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 17 | StageSeventeenPage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 18 | StageEighteenPage.js | ok | ok | ok | ok | ok | — | ok | PASS |
| 19 | StageNineteenPage.js | ok | ok | ok | ok | ok | — | ok | PASS |

**19 stages, 5 gates, 0 failures.**

## What each column means

- **Frontend** — a `Stage<N>Page.js` exists and is wired into the router's stage
  page list.
- **API** — the four shared stage endpoints resolve in the OpenAPI table:
  `submit`, `approve`, `reject`, `snapshots` under
  `/pilots/{pilot_id}/stages/{stage_number}`.
- **Permission** — the stage has at least one editor/submitter and at least one
  approver in `STAGE_MATRIX`, and every role named is a live role.
- **Persistence** — `StageSubmission` and `StageApproval` are written, and an
  `ImmutableSnapshot` is created on approval.
- **Notification** — the stage action routes through
  `_notify_workflow_action`, which resolves recipients from `STAGE_MATRIX` and
  filters on `role.is_active`.
- **Approval** — `approve_stage` and `reject_stage` both exist and are reachable.
- **Gate** — where a gate follows the stage, its code is in `GATE_MATRIX` and
  its owner is a live role.
- **Next** — the following stage exists in the matrix; stage 19 terminates.

## Gates

| Gate | After stage | Owner |
| --- | --- | --- |
| G1 — پذیرش | 2 | pilot_manager |
| G2 — آمادگی فنی | 4 | setup |
| G3 — عملیات | 9 | operations |
| G4 — تجربه | 13 | support |
| G5 — تجاری | 15 | pilot_manager, sales |

G4 moved from `customer_success` to `support` with the role merge. No gate or
stage names a retired role: the stale-role check returns none.

## No stage depends on call integration

The call subsystem was removed in `0021` and the frontend panel with it. Nothing
in the 19 stages requires it — stage 18, which previously displayed a call
requirement, now asks only for `follow_up_registered` plus its five form fields.
`tests/test_call_integration_removed.py` pins this.

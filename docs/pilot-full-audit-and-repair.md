# Pilot platform audit and repair

Eleven issues, each verified before anything was touched. Three turned out to be
real defects and were fixed; the rest were already correct and were left alone.

Baseline: `master` at `ca5aceb`, synced to `origin/master` `c05bf96` during the
audit. Backend 195 passing before the work, 204 after. Frontend 117 before, 123
after.

---

## Issue 1 — Alembic scope

**Test performed.** Searched the tree for `alembic.ini` and `versions/`
directories, read `env.py` to see which metadata it binds, and grepped for
`finance`, `invoice`, `price_version`, `PriceVersion` across every tracked file.

**Was the violation real?** No.

**Evidence.** Exactly one Alembic installation:
`smart-building-backend/alembic.ini` with 23 revisions in a single linear chain,
`0001` → `0023`, one head. `env.py` binds `Base.metadata` from the pilot's own
models. Zero matches for any finance term anywhere in the repository. The only
`estimate` hits are `estimated_cost`, a label in incident reporting.

**Fix.** None needed. Documented the ownership so the question does not have to
be re-derived: `docs/pilot-database-migration-map.md`.

**Result: NO CHANGE REQUIRED** (documentation added).

---

## Issue 2 — Customer success merged into support

**Test performed.** Compared `SUPPORT_PERMISSIONS` against
`CUSTOMER_SUCCESS_PERMISSIONS`, checked `STAGE_MATRIX` and `GATE_MATRIX` for
retired role names, queried the live database for role membership and permission
counts, and ran the merge test suite.

**Was the violation real?** Already fixed in `ca5aceb` before this audit. The
audit confirms the outcome holds.

**Evidence.** 10 live roles; `customer_success` absent from `SYSTEM_ROLES` and
`ROLE_DEFINITIONS`. `support` displays as "پشتیبانی" with 37 permissions —
30 ∪ 29 with 22 shared. `CUSTOMER_SUCCESS_PERMISSIONS ⊆ SUPPORT_PERMISSIONS`
returns true with nothing missing. No stage or gate names the retired role.
Live database: `customer_success` inactive with 0 members and its 29 grants
intact for history; `support` active with 2 members and 37 grants.

A brand-new discovery from that work is worth repeating: **there was never a
separate `training` role**. `support` has been "آموزش/پشتیبانی" with official
code `SUPPORT_TRAINING` since it was defined, so the merge only had to move
`customer_success`.

**Fix.** None needed now.

**Result: PASS.**

---

## Issue 3 — Orphan call UI

**Test performed.** Searched the frontend for `CallsPanel`, `callService`,
`calls.`, `recording-reference`, and for call wording on the stage 18 page.

**Was the violation real?** It was, and it was already removed — by `d3a0aaf`,
a frontend commit that landed during this session.

**Evidence.** `CallsPanel.js`, `callService.js`, `calls.css` and the call tests
no longer exist. No stage page references them. `StageEighteenPage.js` contains
no call wording, so the misleading "a valid call result must be recorded to pass
this stage" message is gone.

**Fix.** None needed.

**Result: PASS.**

---

## Issue 4 — Backend call left optional

**Test performed.** Grepped `app/` for call, astel, voip and recording; listed
ORM tables and RBAC permission codes; checked `config.py` for a call flag.

**Was the violation real?** No — there is nothing left to make optional.

**Evidence.** Zero call references in application code. No call tables in
`Base.metadata`. No `calls.*` permission. No `CALL_*` setting in `config.py`.
The subsystem was fully removed by `0021`/`0022`, and
`tests/test_call_integration_removed.py` fails the build if any of it returns.
All 19 stages pass the cross-cutting audit with call integration absent, which
is the stronger form of "works with it disabled".

**Fix.** None needed. A `CALL_INTEGRATION_ENABLED` flag would guard code that
does not exist.

**Result: NO CHANGE REQUIRED.**

---

## Issue 5 — Git synchronization

**Test performed.** `git fetch --all --prune`, then compared local `master`
against `origin/master` and classified the incoming commits.

**Was the violation real?** Yes — local was three commits behind.

**Evidence.** `c05bf96`, `402efa4`, `a6bef98` — all frontend, all touching the
Jalali date picker: `PersianDatePicker.js`, `jalali-date.css`,
`jalaliDatePicker.test.mjs`. `git merge-base --is-ancestor` confirmed a clean
fast-forward with no local-only commits.

**Fix.** `git pull --ff-only`. No merge commit.

**Files changed.** Three, all incoming from the remote.

**Result: FIXED.**

---

## Issue 6 — Refresh token and session

**Test performed.** Read `sessionStore.js` and `httpClient.js`, then ran the
existing suites `httpClient.test.mjs` and `sessionStore.test.mjs`.

**Was the violation real?** No — the flow was implemented and already covered.

**Evidence.** `sessionStore` persists the access token, refresh token and both
expiry timestamps. `httpClient` holds a module-level `refreshPromise` so
concurrent callers share one refresh, refreshes proactively inside a 60-second
leeway, retries a 401 exactly once, guards the retry with
`sessionStore.getToken() === tokenUsed` so a request that lost the race does not
refresh again, and clears the session when the refresh itself is rejected.
Thirteen tests pass, including "coalesces simultaneous 401 responses into one
rotating refresh" and "does not enter a refresh loop when the retried request is
still unauthorized".

**Fix.** None needed.

**Result: PASS.**

---

## Issue 7 — Roleless user

**Test performed.** Signed in with a mobile never seen before, inspected the
created row, then called eight protected endpoints. Separately, executed
`canAccessRoute` and the router's denial page for a user with no roles.

**Was the violation real?** The backend half was already correct. **The frontend
half was a real defect.**

**Evidence.** Backend: login succeeds, the user row is created active with zero
roles, `/auth/me` and `/auth/bootstrap` return 200 with `scopes: ["READ_ONLY"]`
and an empty menu, and all eight protected calls return 403
`PERMISSION_DENIED`. An admin can then grant a role and the same session gains
access.

Frontend: the person lands on the dashboard, is refused, and reads
*"مجوز لازم برای این مسیر (dashboard.read) در حساب شما وجود ندارد"* — an internal
permission code they cannot act on — under a button linking back to the
dashboard, which refuses them again. Executed proof:

```
canAccessRoute(dashboard) = false
back link -> #/
that route allowed? false
=> dead end: yes
```

**Fix.** Added `accessDeniedReason(route, permissions, roles)` to
`routePermissions.js`. With no roles it returns "هنوز نقشی برای حساب شما تعیین
نشده است" and no return route. With roles it keeps the existing permission
message and offers the dashboard only when the dashboard is actually reachable.
`router.js` renders the reason and appends the link conditionally.

**Files changed.** `src/app/routePermissions.js`, `src/app/router.js`,
`tests/rolelessAccess.test.mjs` (new).

**Tests after fix.** 6 new, frontend suite 117 → 123, all passing.

**Result: FIXED.**

---

## Issue 8 — Notification SMS transaction safety

**Test performed.** Substituted a spy provider, created a notification, rolled
the caller's transaction back, and counted provider calls against surviving
rows.

**Was the violation real?** Yes.

**Evidence, before the fix:**

```
provider calls after create_notification (still uncommitted): 1
-> caller rolled back
notifications after rollback : 0
SMS handed to the provider   : 1
notification row that survived: 0
```

The recipient was texted about a notification that does not exist.

**Fix.** The send decision still happens inside the transaction — every skip
reason (`SMS_DISABLED_FOR_EVENT`, `USER_INACTIVE`, `SMS_RECIPIENT_MISSING`,
`SMS_PREFERENCE_DISABLED`, `SMS_PROVIDER_DISABLED`, `SMS_RECIPIENT_INVALID`)
stays terminal and is written as before. When a send is warranted the delivery
row is written `PENDING`, flushed for its id, and the job queued on
`session.info`. An `after_commit` listener drains the queue, calls the provider
and records the result in its own short session; an `after_rollback` listener
drops it.

A provider exception is caught and recorded as `SMS_DISPATCH_ERROR` rather than
raised, because the business transaction is already committed by then. No queue
system was introduced.

**Files changed.** `app/services/notifications.py`,
`tests/test_notification_sms_transaction.py` (new).

**Tests after fix.** 9 new covering all three required scenarios plus duplicate
suppression and OTP isolation. Backend 195 → 204, all passing.

```
commit success  -> 1 SMS, delivery DELIVERED
rollback        -> 0 SMS, 0 notifications
provider fails  -> business data committed, delivery FAILED
provider raises -> commit does not raise, delivery SMS_DISPATCH_ERROR
two commits     -> 1 SMS, 1 delivery row
```

**Result: FIXED.**

---

## Issue 9 — API prefix

**Test performed.** Counted the OpenAPI paths by prefix.

**Evidence.** 99 endpoints: 14 versioned under `/api/v1` (dashboard, reports),
81 legacy roots, 4 infrastructure paths. The frontend handles both correctly —
each service carries its own base, and `apiRoutes.js` centralises the contract.

**Fix.** None, by product decision. The convention and its guardrail test were
already established in `a1dec8b`: new endpoints go under `/api/v1`, the legacy
roots are frozen, and `tests/test_api_routing_convention.py` fails a router that
drifts.

**Result: DEFERRED BY PRODUCT DECISION.**

---

## Issue 10 — PostgreSQL test isolation

**Test performed.** Ran `tests/test_postgres_integration.py` three times in a
row against the same target, then checked for leftover databases.

**Was the violation real?** It was, and it was fixed earlier in `e475452`. This
audit confirms the fix holds.

**Evidence.**

```
run 1: 7 passed
run 2: 7 passed
run 3: 7 passed
leftover bambo_test_* databases: 0
```

The suite creates `bambo_test_<id>` per session, migrates it through Alembic to
the real head, and drops it in teardown after disposing the engine and
terminating stragglers. The environment variable now names a server, not the
database under test, so a mistyped value cannot write into a development
database.

**Fix.** None needed.

**Result: PASS.**

---

## Issue 11 — Pilot report scope

**Test performed.** Inventoried every dashboard and report route, extracted the
KPI keys, grepped the report and dashboard services for financial vocabulary,
and scanned every ORM column for financial names.

**Was the violation real?** No.

**Evidence.** The nine KPIs are all pilot workflow:
`floors_completed_on_plan_percent`, `successful_upload_percent`,
`recapture_percent`, `correct_floor_assignment_percent`,
`successful_notification_percent`, `successful_training_percent`,
`continuation_interest_percent`, `proposal_ready_percent`,
`average_satisfaction_score`.

No financial column exists in any of the 40 tables — the single match when
scanning for `cost|price|amount|invoice|estimate|fee|payment` was
`form_f01.feedback_actual`, a substring false positive.

The one apparent exception is `EVIDENCE_LABELS`, which includes "برآورد هزینه"
and "هزینه انجام‌شده". It is used in exactly one place, the
`/reports/pilots/{id}/external-evidence` endpoint, which reports whether a
capability **exists on the main platform** — `checked`, `checked_by`,
`checked_at` and a result string capped at 500 characters. That is the minimal
external reference this issue permits, not a duplicated calculation.

**Fix.** None needed.

**Result: NO CHANGE REQUIRED.**

---

## 19-stage cross-cutting audit

Full matrix in `docs/pilot-19-stage-audit.md`.

**19 stages, 5 gates, 0 failures.** Every stage resolves UI → permission → API →
persistence → notification → approval → gate → next-stage unlock, and every role
named by a stage or gate is a live role. G4 now belongs to `support`.

---

## Summary

| # | Issue | Status |
| --- | --- | --- |
| 1 | Alembic scope | NO CHANGE REQUIRED |
| 2 | Customer success → support | PASS |
| 3 | CallsPanel removal | PASS |
| 4 | Optional backend call | NO CHANGE REQUIRED |
| 5 | Git synchronization | FIXED |
| 6 | Refresh token | PASS |
| 7 | Roleless user | FIXED |
| 8 | SMS transaction safety | FIXED |
| 9 | API prefix | DEFERRED BY PRODUCT DECISION |
| 10 | PostgreSQL test isolation | PASS |
| 11 | Pilot report scope | NO CHANGE REQUIRED |
| — | 19-stage audit | PASS |

## Regression

| Suite | Result |
| --- | --- |
| Backend | 204 passed, 7 skipped |
| PostgreSQL integration, three consecutive runs | 7 passed each |
| Frontend `npm run check` | pass |
| Frontend `npm test` | 123 passed |
| `alembic heads` | `0023_merge_customer_success_into_support`, single head |

Live smoke test against the running stack: health ready with database, migration
and storage all true; login as the merged support role returns 37 permissions
and a refresh token; `/auth/me`, `/auth/bootstrap`, `/pilots`, `/notifications`
and `/api/v1/dashboard/summary` all return 200. `/api/v1/reports/kpis` returns
403 for that role, which is correct — `reports.kpi` is not a support permission.

## Finance

```
Finance files changed by this audit: NONE
```

There is no Finance module in this repository to change. No `REVERT ONLY` file.

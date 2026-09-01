# API routing convention

The backend serves two route shapes. This document freezes that split so it
stops spreading, and states the rule for everything written from now on.

**Nothing in this document changes an existing route.** No renames, no
redirects, no aliases. The current surface is what the frontend is built
against and it stays exactly as it is.

## The rule

> **Every new endpoint is registered under `/api/v1/`.**
>
> The legacy roots listed below are closed. They accept no new top-level
> prefix, and a new router never joins them.

`tests/test_api_routing_convention.py` enforces this. A router registered
outside the frozen legacy allowlist without `/api/v1` fails the suite.

## Current inventory

99 endpoints, taken from the live OpenAPI schema.

### Versioned — 14 endpoints

| Prefix | Endpoints | Router |
| --- | --- | --- |
| `/api/v1/dashboard` | 4 | `app/routers/dashboard.py` |
| `/api/v1/reports` | 10 | `app/routers/reports.py` |

These two are the pattern to copy.

### Legacy — 81 endpoints, closed to new prefixes

| Prefix | Endpoints | Router |
| --- | --- | --- |
| `/pilots` | 39 | `pilots.py`, `product.py`, `operations.py`, `experience.py`, `evaluation.py`, `commercial.py`, `forms.py` |
| `/roles` | 8 | `security.py` |
| `/auth` | 7 | `security.py` |
| `/notifications` | 6 | `notifications.py` |
| `/users` | 6 | `security.py` |
| `/missions` | 5 | `operations.py` |
| `/floors` | 4 | `product.py` |
| `/incidents` | 3 | `experience.py` |
| `/audit` | 1 | `security.py` |
| `/dwg` | 1 | `product.py` |
| `/notification-preferences` | 1 | `notifications.py` |

Several routers mount paths under `/pilots` without carrying a prefix of their
own — `product.py`, `experience.py` and friends declare
`APIRouter(tags=[...], dependencies=[...])` and spell the full path on each
decorator. That is why the router count exceeds the prefix count.

### Infrastructure — 4 endpoints, permanently unversioned

| Path | Why it is exempt |
| --- | --- |
| `/health` | probe target |
| `/health/live` | liveness probe |
| `/health/ready` | readiness probe, gates traffic |
| `/version` | release identification |

Load balancers, orchestrators and uptime checks point at fixed paths. Versioning
them would mean re-pointing infrastructure for no benefit. They are exempt by
design, not by neglect, and they are not "legacy".

## Writing a new endpoint

```python
# app/routers/webhooks.py
router = APIRouter(prefix="/api/v1/webhooks", tags=["webhooks"])

@router.post("/inbound")
def receive_inbound(...): ...
```

The prefix belongs on the `APIRouter`, not repeated on each decorator. A router
whose paths span several resources still carries `/api/v1` on the router and
spells the rest per route:

```python
router = APIRouter(prefix="/api/v1", tags=["capture"])

@router.get("/sites/{site_id}/captures")
def list_captures(...): ...
```

### Extending a legacy tree

Adding a route under an existing legacy prefix — a new `/pilots/...` path, say —
is allowed, because splitting one resource across two versions is worse than
leaving it whole. The guardrail test pins the legacy endpoint count, so doing it
is a deliberate edit with a visible diff rather than a silent drift.

Prefer `/api/v1` whenever the new endpoint is genuinely a new resource.

## Naming

| Rule | Yes | No |
| --- | --- | --- |
| Plural collections | `/api/v1/missions` | `/api/v1/mission` |
| Kebab-case multi-word segments | `/api/v1/notification-preferences` | `/api/v1/notification_preferences`, `/api/v1/notificationPreferences` |
| Snake_case path parameters | `{pilot_id}`, `{stage_number}` | `{pilotId}` |
| Nouns for resources, verbs only for actions | `/api/v1/pilots/{pilot_id}` | `/api/v1/getPilot` |
| Lowercase throughout | `/api/v1/dwg` | `/api/v1/DWG` |

A singular segment is correct only when the resource is genuinely singular for
its parent — `/pilots/{pilot_id}/commercial-proposal` is one proposal per pilot,
and that reads better than a collection of one.

### Action endpoints

State transitions that are not plain CRUD get a verb as the final segment,
following the existing stage routes:

```
POST /api/v1/<collection>/{id}/<verb>
```

Matching what is already there: `submit`, `approve`, `reject`, `close`,
`approve` on final outcome. Use `POST`, and keep the verb a single word.

## Trailing slashes

No route ends in `/`. Every one of the 99 current paths already complies.

Starlette's `redirect_slashes` stays at its default `True`, so a client that
sends `/api/v1/missions/` receives a `307` to the canonical path. Rely on that
as a safety net, never as the documented path — clients should send the exact
form, since a `307` costs a round trip and some HTTP clients drop the
`Authorization` header when they follow a redirect.

## Nesting

Nest only to express ownership, and stop at two identifiers:

```
/api/v1/pilots/{pilot_id}/missions            collection owned by a pilot
/api/v1/missions/{mission_id}/floors/{floor_id}   the deepest shape in use
```

Once a resource has its own identifier, address it at the top level instead of
threading the parent through. The existing routes already do this — a mission is
created at `/pilots/{pilot_id}/missions` but read at `/missions/{mission_id}`,
and an incident at `/incidents/{incident_id}`.

Three identifiers in one path means the middle one is redundant. Split it.

## Versioning beyond v1

`v1` changes only for a break clients cannot absorb: a field removed, a type
changed, a status code repurposed. Additive changes — a new optional field, a
new endpoint, a new enum member clients may ignore — stay in `v1`.

When `v2` arrives it is a new prefix served alongside `v1`, not a rewrite of it.

## Why the split exists

`/api/v1` was introduced with `dashboard` and `reports`; the earlier routers
were already live and were left alone. The frontend handles both correctly —
each service module carries its own base — so nothing is broken today.

The cost is not runtime, it is guessing. A developer adding an endpoint has to
know which style applies, and the call subsystem removed in `0d2997e` picked
`/api/v1` while the frontend service that consumed it outlived the backend. This
rule removes the guess: new work is versioned, old work is untouched.

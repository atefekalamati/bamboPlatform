# Pilot database migration map

Which migration belongs to which domain, and which are safe to touch.

## Scope finding

The repository contains **one** Alembic installation:

```
smart-building-backend/alembic.ini
smart-building-backend/alembic/versions/   (23 revisions)
```

`alembic/env.py` binds `target_metadata = Base.metadata` from
`app.database`, and the models it imports are the pilot's own. There is no
second `alembic.ini`, no second `versions/` directory, and no Finance module in
this repository — `git grep` for `finance`, `invoice`, `price_version` and
`PriceVersion` across the tree returns nothing.

**Every revision below belongs to the pilot.** No migration here is shared with
or owned by another domain, so the "safe to touch" column is about migration
hygiene, not ownership.

The only `estimate` matches in the tree are `estimated_cost` — a label in the
incident/evidence reporting, not a financial model — and neither file it appears
in is part of any migration.

## Chain

Linear, single head, `0001` → `0023`.

| Revision | Domain | Tables affected | Pilot? | Finance? | Safe to touch? |
| --- | --- | --- | --- | --- | --- |
| `0001_bambo_initial` | Pilot | pilots, pilot_stages, pilot_gates, stage_submissions, stage_approvals, immutable_snapshots, buildings, equipment, sensors | yes | no | no — released |
| `0002_auth_rbac_audit` | Pilot | users, roles, permissions, role_permissions, user_roles, auth_sessions, otp_requests, audit_logs | yes | no | no — released |
| `0003_project_forms_dwg` | Pilot | projects, owners, contacts, floors, dwg_files, dwg_versions | yes | no | no — released |
| `0004_missions_f03_operations` | Pilot | missions, mission_floors, notifications | yes | no | no — released |
| `0005_customer_experience_incidents` | Pilot | incidents, external_evidence_checks, external_platform_references | yes | no | no — released |
| `0006_continuation_evaluation_g5` | Pilot | continuation_reviews, pilot_evaluations | yes | no | no — released |
| `0007_commercial_final_outcome` | Pilot | commercial_proposals, customer_follow_ups, final_outcomes | yes | no | no — released |
| `0008_floor_dwg_reference` | Pilot | floors | yes | no | no — released |
| `0009_incident_unique_cleanup` | Pilot | incidents (constraint) | yes | no | no — released |
| `0010_stage_1_12_alignment` | Pilot | pilot_stages (data) | yes | no | no — released |
| `0011_optional_stage17_proposal_pdf` | Pilot | commercial_proposals | yes | no | no — released |
| `0012_stage_13_19_g5_alignment` | Pilot | pilot_stages, pilot_gates (data) | yes | no | no — released |
| `0013_user_preferences_audit_metadata` | Pilot | user_preferences, audit_logs | yes | no | no — released |
| `0014_in_app_notifications_delivery` | Pilot | notifications, notification_deliveries | yes | no | no — released |
| `0015_incident_lifecycle_hardening` | Pilot | incidents | yes | no | no — released |
| `0016_form_f04_other_issue_description` | Pilot | form_f04 | yes | no | no — released |
| `0017_pilot_scope_and_sms_delivery` | Pilot | pilots, otp_requests | yes | no | no — released |
| `0018_call_integration` | Pilot | calls, call_attempts, call_outcomes, call_webhook_events | yes | no | no — released |
| `0019_user_own_name_edit_permission` | Pilot | users | yes | no | no — released |
| `0020_refresh_tokens` | Pilot | auth_sessions | yes | no | no — released |
| `0021_remove_call_integration` | Pilot | drops the four call tables | yes | no | no — released |
| `0022_remove_call_permissions` | Pilot | permissions, role_permissions (data) | yes | no | no — released |
| `0023_merge_customer_success_into_support` | Pilot | roles, user_roles (data) | yes | no | no — released |

Head: `0023_merge_customer_success_into_support`, verified with `alembic heads`.

## Rules that follow from this

- A new pilot schema change is a new revision on this chain. There is no other
  chain to choose between.
- No released revision above is rewritten. `0021` and `0022` retire the call
  subsystem by adding revisions, not by editing `0018`.
- `tests/test_migrations.py` and `tests/test_postgres_integration.py` both read
  the expected head from `ScriptDirectory` rather than a literal, so adding a
  revision cannot make them stale.

# Legacy SQLite snapshots — archived, do not reuse

These files are the old development database from before the pilot data moved to
PostgreSQL. They are kept only as a rollback copy.

- `bambo-display.backup-20260802-0215.db` — snapshot of 2026-08-02. Held the real
  pilot data: 4 users with roles, 2 pilots (`PIL-1405-001`, `PIL-1405-002`),
  2 projects, 2 owners, 3 contacts, 2 floors, 38 pilot stages, 10 gates,
  24 submissions, 24 approvals, 24 immutable snapshots, 1 mission, F01/F02/F03,
  1 notification and 148 audit entries. **All of it was imported into PostgreSQL
  on 2026-08-21.**
- `bambo-display.db` — the file that replaced it on 2026-08-03. Only ever held
  2 users, 7 sessions and 19 audit rows, with no roles and no pilots. Nothing of
  value, so nothing was imported from it.

Not imported from the snapshot, on purpose:

- `auth_sessions` and `otp_requests` — expired login tokens and one-time codes,
  not business data. `audit_logs.session_id` was therefore stored as NULL; every
  other audit column was preserved.
- The custom role `project03` — it existed in SQLite but was assigned to no user.
  Recreate it from the roles screen if it is still wanted.

The only development database now is the PostgreSQL service in `compose.yaml`,
published on host port 5433 and backed by the Docker volume
`bambo_pilot_postgres_data`.

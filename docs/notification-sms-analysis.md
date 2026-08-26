# Notification SMS reminders — analysis and fix

## Symptom

OTP SMS reached real handsets, but pilot users never received the reminder SMS
that should follow an in-app notification. The in-app notification itself was
always created, so the failure was silent from the UI.

## Root cause: two disagreeing defaults

`sms_enabled` had two different default values in two places.

| Location | Value |
| --- | --- |
| `app/schemas/notifications.py` — `NotificationPreferences.sms_enabled` | `True` |
| `app/services/notifications.py` — `_preferences_dict()` → `raw.get("sms_enabled", False)` | `False` |

Which one applied depended on whether the user had a `user_preferences` row:

```
user created                    -> no preferences row -> schema default  -> True
   |
   +-- first login
       /auth/bootstrap runs _get_or_create_preferences()
       UserPreference(user=user)  ->  notification_preferences = {}
   |
   v
row exists, key missing          -> service default   -> False
```

`UserPreference.notification_preferences` is `Column(JSON_TYPE, default=dict)`,
so a freshly bootstrapped row holds `{}`. `raw.get("sms_enabled", False)` read
that empty blob as an explicit "off".

Because `/auth/bootstrap` runs on every login, **every real user was switched
off the moment they first signed in**. Only `CRITICAL` traffic survived, since
`sms_allowed()` checks `critical_sms_enabled` before `sms_enabled`.

### Second cause: category policy

Even with SMS on, `DEFAULT_SMS_CATEGORIES` had `STAGE: False` and
`PILOT: False`, so the three most common events produced no reminder:

- `stage.review_required`
- `stage.revision_required`
- `stage.action_required`

## Measured before the fix

Spy provider substituted for the transport; the notification path was real.

| User state | Category | Priority | SMS | Reason |
| --- | --- | --- | --- | --- |
| no preferences row | STAGE | HIGH | no | `SMS_PREFERENCE_DISABLED` |
| no preferences row | MISSION | HIGH | yes | delivered |
| after first login | STAGE | HIGH | no | `SMS_PREFERENCE_DISABLED` |
| after first login | MISSION | HIGH | no | `SMS_PREFERENCE_DISABLED` |
| after first login | INCIDENT | HIGH | no | `SMS_PREFERENCE_DISABLED` |
| after first login | INCIDENT | CRITICAL | yes | delivered |
| after first login | COMMERCIAL | NORMAL | no | `SMS_PREFERENCE_DISABLED` |
| after first login | PILOT | NORMAL | no | `SMS_PREFERENCE_DISABLED` |

## Fix

One policy, defined once, in `app/schemas/notifications.py`:

```python
DEFAULT_IN_APP_ENABLED = True
DEFAULT_SMS_ENABLED = True
DEFAULT_CRITICAL_SMS_ENABLED = True

DEFAULT_SMS_CATEGORIES = {
    "AUTH": False,      # OTP owns its own flow
    "PILOT": True,
    "STAGE": True,
    "MISSION": True,
    "INCIDENT": True,
    "SLA": True,
    "COMMERCIAL": True,
    "SYSTEM": False,    # broadcast noise stays opt-in
}
```

`app/services/notifications.py` imports those constants instead of defining its
own, and re-exports `DEFAULT_SMS_CATEGORIES` so existing importers keep working.

A missing key now means "the user has not chosen", not "off":

```python
sms_enabled=raw.get("sms_enabled", DEFAULT_SMS_ENABLED)
```

`_merge_sms_categories()` layers stored per-category choices over the defaults,
so a legacy `sms_categories: {}` blob no longer mutes every category, and a
partial `{"STAGE": false}` mutes only STAGE.

`_create_sms_delivery()` gained an inactive-account guard that records
`USER_INACTIVE` as a `SKIPPED` delivery while keeping the in-app record.

## What was deliberately left alone

- SMS provider and the IPPanel adapter
- OTP request/verify and its pattern payload
- `create_notification` structure, recipient resolution, `NotificationDelivery`
- The generic reminder body
- `_get_or_create_preferences` — writing a frozen snapshot of the defaults into
  new rows would fork the policy; `{}` meaning "no choice" keeps one source of
  truth and needs no data migration.

## Explicit user choices are preserved

| Stored blob | Result |
| --- | --- |
| `{}` | defaults apply — reminders on |
| `{"sms_enabled": false}` | stays off |
| `{"sms_enabled": true, "sms_categories": {"STAGE": false}}` | STAGE off, others default |

No `UPDATE ... SET sms_enabled = true` was run and none is needed.

**Database migration required: No.** `notifications`, `notification_deliveries`
and `user_preferences` already carry every column this behaviour uses. The
change is runtime policy only.

## Transaction boundary

`create_notification()` sends the SMS inside the caller's transaction, before
`db.commit()`. Reviewed each caller: every `db.rollback()` in
`workflow.py` (1082, 1258, 1324), `experience.py` (916) and `operations.py`
(217) executes *before* its notification call, and `db.commit()` follows the
notify call within a few statements. The only remaining window is a failure of
the final commit itself.

Not changed here — deferring the send to an `after_commit` hook is a real
architectural change and this task called for the minimal fix. Logged as a
known narrow risk.

## Duplicate suppression

Already handled and now covered by a test. Every call site passes a
`deduplication_key`:

| Site | Key |
| --- | --- |
| `workflow.py:130` | stage + version scoped |
| `operations.py:149` | `{event}:{mission}:{updated_at}` |
| `experience.py:950…1184` | incident id + recipient/status |
| `experience.py:556` | `pilot.main_output_ready:{pilot}:{stage}` |
| `commercial.py:94` | `commercial.followup_due:{pilot}:{due}` |

A repeat dispatch returns the existing `Notification` before
`_create_sms_delivery()` runs, so one notification yields at most one SMS row.

## Reminder text

```
یادآوری بامبو:
لطفاً اعلان جدید سامانه را بررسی کرده و اقدام الزامی خود را انجام دهید.
```

Plus `PLATFORM_LOGIN_URL` when configured. Carries no pilot code, owner name,
incident detail, commercial data, token or OTP — asserted by test.

## Delivery outcomes

| Condition | Status | `failure_code` |
| --- | --- | --- |
| event opted out of SMS | SKIPPED | `SMS_DISABLED_FOR_EVENT` |
| recipient account disabled | SKIPPED | `USER_INACTIVE` |
| no mobile on record | SKIPPED | `SMS_RECIPIENT_MISSING` |
| user preference off | SKIPPED | `SMS_PREFERENCE_DISABLED` |
| `SMS_ENABLED=false` | SKIPPED | `SMS_PROVIDER_DISABLED` |
| malformed mobile | FAILED | `SMS_RECIPIENT_INVALID` |
| provider rejected | FAILED | provider code |

A provider failure never rolls back the business action and never deletes the
in-app notification.

# سند اسکیما و تنظیمات دیتابیس BAMBO

تاریخ استخراج: ۱۴۰۵/۰۵/۱۲  
منبع: مدل‌های SQLAlchemy، Migrationهای Alembic و تنظیمات واقعی Backend

## ۱. وضعیت دیتابیس فعال

```text
DBMS: PostgreSQL
Driver: psycopg
Host: localhost
Port: 5433
Database: bambo
User: bambo
Password: ***
Migration: 0016_form_f04_other_issue_description (head)
```

قالب رشته اتصال:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DATABASE
```

پورت داخلی PostgreSQL در Docker برابر `5432` است و در محیط توسعه روی پورت `5433` سیستم میزبان منتشر می‌شود.

## ۲. نمای کلی ارتباط جداول

```text
users
 ├── user_roles ── roles ── role_permissions ── permissions
 ├── auth_sessions
 ├── user_preferences
 └── audit_logs

pilots
 ├── projects ── owners ── contacts
 │              └── floors ── dwg_files ── dwg_versions
 ├── pilot_stages
 │    └── stage_submissions
 │         └── stage_approvals
 │              └── immutable_snapshots
 ├── pilot_gates
 ├── form_f01
 ├── form_f02
 ├── form_f04
 ├── missions
 │    ├── form_f03
 │    ├── mission_floors
 │    └── continuation_reviews
 ├── incidents
 ├── notifications ── notification_deliveries
 ├── external_platform_references
 ├── external_evidence_checks
 ├── pilot_evaluations
 ├── commercial_proposals
 ├── customer_follow_ups
 └── final_outcomes
```

تعداد جداول مدل فعلی: **۴۰ جدول**.

## ۳. هویت، نشست و دسترسی

### users

| ستون | نوع | توضیح |
|---|---|---|
| id | Integer, PK | شناسه کاربر |
| mobile | Varchar(20), Unique | شماره موبایل |
| display_name | Varchar(120) | نام نمایشی |
| is_active | Boolean | وضعیت فعال |
| locked_at | DateTime, Nullable | زمان قفل‌شدن |
| last_login_at | DateTime, Nullable | آخرین ورود |
| created_at / updated_at | DateTime | زمان ایجاد و تغییر |

### roles

`id`, `name` (Unique)، `display_name`، `is_system`، `is_active`، `created_at`، `updated_at`.

### permissions

`id`, `code` (Unique)، `group_name`، `description` و `is_sensitive`.

### user_roles

جدول واسط چندبه‌چند با کلید مرکب `user_id + role_id` و ستون `assigned_at`.

### role_permissions

جدول واسط چندبه‌چند با کلید مرکب `role_id + permission_id` و ستون `assigned_at`.

### auth_sessions

`id`, `user_id`, `token_hash` (Unique)، `created_at`، `expires_at`، `last_used_at` و `revoked_at`.

Token خام ذخیره نمی‌شود و فقط Hash آن در دیتابیس قرار می‌گیرد.

### otp_requests

`id`, `public_id`, `mobile`, `purpose`, `code_hash`, `status`, `attempts`, `max_attempts`, `provider_status`, `request_ip`, `expires_at`, `created_at`, `verified_at`.

کد OTP به‌صورت Hash ذخیره می‌شود و کد خام در دیتابیس قرار نمی‌گیرد.

### user_preferences

`user_id`, `language`, `theme`, `timezone`, `calendar`, `page_size`, `default_page`, `last_page` و ستون‌های JSON زیر:

- `visible_columns`
- `column_order`
- `saved_filters`
- `notification_preferences`
- `dashboard_preferences`

مقادیر پیش‌فرض تقویم و منطقه زمانی `jalali` و `Asia/Tehran` هستند.

### audit_logs

`actor_user_id`, `action`, `entity_type`, `entity_id`, `pilot_id`, `old_data`, `new_data`, `reason`, `request_id`, `ip_address`, `user_agent`, `session_id`, `created_at`.

اطلاعات قبل و بعد تغییر در ستون‌های JSON ذخیره می‌شود.

## ۴. پرونده، پروژه و مالک

### pilots

`id`, `code`, `pilot_year`, `sequence`, `project_number`, `project_system_name`, `display_name`, `status`, `current_stage`, `created_at`, `updated_at`.

فیلدهای `code`، `project_number` و `project_system_name` یکتا هستند.

### projects

`id`, `pilot_id`, `owner_id`, `system_name`, `display_name`, `name`, `total_floors`, `address`, `progress_stage`, `customer_need`, `expected_value`, `created_at`, `updated_at`.

هر Pilot یک Project دارد و `pilot_id` یکتا است.

### owners

`id`, `name`, `decision_maker_name`, `decision_maker_position`, `primary_mobile`, `created_at`, `updated_at`.

### contacts

`owner_id`, `name`, `position`, `mobile`, `is_primary`, `is_site_coordinator`, `created_at`.

## ۵. مراحل، Gateها و Snapshot

### pilot_stages

`id`, `pilot_id`, `number`, `title`, `status`, `latest_version`, `submitted_at`, `approved_at`, `created_at`, `updated_at`.

### pilot_gates

`id`, `pilot_id`, `code`, `title`, `after_stage`, `status`, `passed_at`.

### stage_submissions

`id`, `stage_id`, `version`, `status`, `form_data` (JSON)، `checklist` (JSON)، `submitted_by`, `submitted_at`.

### stage_approvals

`id`, `submission_id` (Unique)، `decision`, `reviewer`, `reason`, `correction_items` (JSON)، `reviewed_at`.

### immutable_snapshots

`id`, `approval_id` (Unique)، `pilot_id`, `stage_number`, `version`, `name`, `content` (JSON)، `content_hash`, `created_at`.

### روند ذخیره مرحله

1. مرحله جاری در `pilots.current_stage` نگهداری می‌شود.
2. وضعیت مستقل هر مرحله در `pilot_stages.status` قرار می‌گیرد.
3. هر Submit یک نسخه در `stage_submissions` می‌سازد.
4. فرم و چک‌لیست متغیر مرحله در JSON ذخیره می‌شوند.
5. تصمیم تأیید یا رد در `stage_approvals` ثبت می‌شود.
6. پس از تأیید، Snapshot تغییرناپذیر همراه `content_hash` ساخته می‌شود.

## ۶. فرم F01

جدول `form_f01`:

```text
id
pilot_id
case_owner_user_id
project_active
imaging_value
remote_viewing_need
access_possible
dwg_available
continued_capacity
not_demo_only
introduction_completed
imaging_accepted
dwg_accepted
feedback_accepted
coordinator_name
coordinator_mobile
limitation
result
referral_deadline
sales_user_id
pilot_manager_user_id
referred_at
created_at
updated_at
```

## ۷. فرم F02

جدول `form_f02`:

```text
id
pilot_id
responsible_user_id
information_package
contacts_summary
progress_status
limitation
main_project_registered
floor_order_confirmed
typical_floors_identified
plan_connections_registered
start_point_registered
expert_access_tested
main_app_display_tested
ready_for_capture
ambiguity
referred_at
configured_by_user_id
controlled_by_user_id
configured_at
created_at
updated_at
```

## ۸. فرم F03

فرم F03 به Mission متصل است و در جدول `form_f03` ذخیره می‌شود:

```text
id
mission_id
responsible_user_id
assignment_accepted
site_entry_confirmed
permission_confirmed
ppe_ready
camera_ready
main_app_connected
battery_ready
storage_ready
project_floor_plan_confirmed
test_image_completed
stop_condition_reason
mission_completed
operations_confirmed
started_at
finished_at
created_at
updated_at
```

## ۹. فرم F04

جدول `form_f04` شامل گروه‌های اطلاعاتی زیر است:

- مسئول فرم و Pilot
- ورود مالک و بازکردن پروژه
- مشاهده تور و تکمیل آموزش
- نتیجه مشاهده و شرح مشکل
- `other_issue_description` برای مشکل دستی
- دسته، مسیر، مسئول و موعد مشکل
- پیگیری اول و دوم
- امتیاز پوشش، کیفیت و رضایت
- بخش مفید، بخش ناقص و کاربران دیگر
- نیاز به آموزش بیشتر
- علاقه به ادامه و آمادگی پیشنهاد
- ارزش ایجادشده و مانع خرید
- تعداد پروژه، دفعات استفاده و تعداد کاربر
- تصمیم‌گیرنده، اقدام بعدی و نتیجه نهایی
- مسئول موفقیت مشتری، فروش و مدیر پایلوت
- چک‌لیست کامل آموزش
- `viewed_sections` به‌صورت JSON
- تعداد ورود به پلتفرم اصلی
- نتیجه کاهش بازدید و تصمیم نهایی

### F05

در ساختار فعلی جدول مستقلی با نام F05 وجود ندارد. اطلاعات نهایی آن بین جداول زیر تقسیم شده است:

- `commercial_proposals`
- `customer_follow_ups`
- `final_outcomes`
- `pilot_evaluations`

## ۱۰. مأموریت‌ها و طبقات

### missions

`id`, `pilot_id`, `sequence`, `code`, `expert_user_id`, `scheduled_start`, `scheduled_end`, `location`, `site_contact_name`, `site_contact_mobile`, `limitation`, `status`, `sla_due_at`, `created_by_user_id`, `created_at`, `updated_at`.

### floors

`id`, `project_id`, `code`, `name`, `level_order`, `floor_type`, `dwg_reference_confirmed`, `dwg_reference_confirmed_at`, `dwg_reference_confirmed_by_user_id`, `created_at`, `updated_at`.

### mission_floors

```text
mission_id
floor_id
capture_state
correct_floor
start_point_confirmed
main_capture_started
continuous_route
coverage_completed
capture_finished
saved_in_main_app
capture_started_at
capture_finished_at
main_upload_started
main_upload_completed
correct_floor_link
operations_notified
failure_reason
updated_at
```

### continuation_reviews

`mission_id`, `responsible_user_id`, تأیید Stageهای ۵ تا ۱۳، `independent_result`, `created_at`, `updated_at`.

## ۱۱. فایل DWG

### dwg_files

`id`, `floor_id` (Unique)، `created_at`.

### dwg_versions

`id`, `dwg_file_id`, `version`, `original_filename`, `standardized_filename`, `storage_key`, `mime_type`, `size_bytes`, `sha256`, `dwg_signature`, `is_readable`, `uploaded_by_user_id`, `uploaded_at`.

فایل باینری DWG در PostgreSQL قرار نمی‌گیرد. فایل در Storage ذخیره می‌شود و فقط مسیر، Metadata، حجم، Signature و SHA-256 در دیتابیس ثبت می‌شود.

## ۱۲. رخدادها

جدول `incidents`:

```text
id
pilot_id
mission_id
sequence
code
occurred_at
reported_at
reported_by_user_id
stage_number
severity
incident_type
location
description
containment_action
notified_people (JSON)
informed_at
root_cause
corrective_action
preventive_action
owner_user_id
response_due_at
correction_due_at
responded_at
contained_at
result
evidence
lessons_learned
status
closed_by_user_id
closed_at
closure_note
closure_approved_by_user_id
created_at
updated_at
```

روی وضعیت، شدت، نوع، Stage، مسئول، کد و موعدهای رخداد Index وجود دارد.

## ۱۳. اعلان‌ها

### notifications

```text
id
public_id
mission_id
pilot_id
recipient_user_id
actor_user_id
recipient_mobile
channel
notification_type
category
priority
title
body
short_body
entity_type
entity_id
action_url
template
payload (JSON)
status
provider_status
attempts
last_error
alternate_contact_method
is_read
read_at
expires_at
deleted_at
deduplication_key
sent_at
created_at
updated_at
```

### notification_deliveries

`notification_id`, `channel`, `recipient_address`, `provider`, `template_code`, `status`, `provider_message_id`, `attempt_count`, `next_retry_at`, `sent_at`, `delivered_at`, `failed_at`, `failure_code`, `failure_reason`, `created_at`, `updated_at`.

## ۱۴. تجربه مشتری و شواهد خارجی

### external_platform_references

وضعیت پروژه اصلی، شروع پردازش، تشخیص مسیر، اتصال پلان، آماده‌بودن تور و بررسی برداشت‌ها را برای هر Pilot نگهداری می‌کند.

### external_evidence_checks

`pilot_id`, `capability`, `status`, `checked_by_user_id`, `checked_at`, `result`, `created_at`, `updated_at`.

## ۱۵. ارزیابی و تجارت

### pilot_evaluations

وضعیت و نتیجه حوزه‌های عملیات، کیفیت، فنی، مشتری و تجاری به‌همراه `one_page_summary`.

### commercial_proposals

`pilot_id`, `responsible_user_id`, `project_count`, `floor_count`, `area_sqm`, `frequency`, `period`, `user_count`, `support_scope`, `features` (JSON)، مشخصات فایل پیشنهاد، `decision_maker`, `follow_up_at`, `created_at`, `updated_at`.

### customer_follow_ups

`pilot_id`, `schedule_slot`, `obstacle`, `action`, `owner_user_id`, `due_at`, `result`, `completed_at`, `created_at`, `updated_at`.

### final_outcomes

`pilot_id`, `responsible_user_id`, `outcome`, `reason`, `ready_at`, `success_owner_user_id`, `periodic_capture`, `contracted_user_count`, `first_capture_at`, `pilot_manager_approved`, `approved_by_user_id`, `approved_at`, `created_at`, `updated_at`.

## ۱۶. جداول ساختمان هوشمند عمومی

### buildings

`id`, `name`, `address`, `description`, `total_floors`, `status`, `created_at`, `updated_at`.

### equipment

`id`, `name`, `equipment_type`, `model`, `status`, `building_id`, `created_at`, `updated_at`.

### sensors

`id`, `name`, `sensor_type`, `unit`, `location`, `status`, `equipment_id`, `created_at`, `updated_at`.

این سه جدول از ساختار عمومی Smart Building باقی مانده‌اند و از جریان اصلی ۱۹ مرحله Pilot جدا هستند.

## ۱۷. تنظیمات Database Engine

```env
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=1800
DB_STATEMENT_TIMEOUT_MS=15000
DB_SSLMODE=require
```

ویژگی‌های Engine:

- `pool_pre_ping=true`
- `application_name=bambo-backend`
- Timezone اتصال دیتابیس: UTC
- `statement_timeout`: پیش‌فرض ۱۵ ثانیه
- `autocommit=false`
- `autoflush=false`
- `future=true`
- Migrationهای Production فقط با Alembic
- SQLite فقط برای تست و محیط مجزا
- SQLite در Production ممنوع

## ۱۸. تنظیمات Development

```env
DATABASE_URL=postgresql+psycopg://bambo:***@localhost:5433/bambo
APP_ENV=development
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=1800
DB_STATEMENT_TIMEOUT_MS=15000
```

Docker Development:

```yaml
image: postgres:17-alpine
database: bambo
user: bambo
host_port: 5433
container_port: 5432
volume: bambo_postgres_data
```

## ۱۹. تنظیمات Production

```env
APP_ENV=production
DATABASE_URL=postgresql+psycopg://runtime_user@db:5432/bambo?sslmode=require
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT_SECONDS=30
DB_POOL_RECYCLE_SECONDS=1800
DB_STATEMENT_TIMEOUT_MS=15000
DB_SSLMODE=require
```

در Production:

- رمز دیتابیس از Docker Secret یا Secret Manager دریافت می‌شود.
- PostgreSQL در شبکه داخلی Docker قرار دارد.
- Storage دیتابیس روی Volume دائمی `postgres_data` است.
- Healthcheck با `pg_isready` انجام می‌شود.
- Backend فقط بعد از اجرای موفق Migration شروع می‌شود.
- URL دیتابیس باید صراحتاً PostgreSQL باشد.
- SSL با `sslmode=require` فعال می‌شود.

## ۲۰. Alembic و Migrationها

دستورات اصلی:

```cmd
python -m alembic current
python -m alembic heads
python -m alembic upgrade head
python -m alembic downgrade -1
```

زنجیره Migration:

```text
0001_bambo_initial_schema.py
0002_auth_rbac_audit.py
0003_project_forms_dwg.py
0004_missions_f03_operations.py
0005_customer_experience_incidents.py
0006_continuation_evaluation_g5.py
0007_commercial_final_outcome.py
0008_floor_dwg_reference.py
0009_incident_unique_cleanup.py
0010_stage_1_12_alignment.py
0011_optional_stage17_proposal_pdf.py
0012_stage_13_19_g5_alignment.py
0013_user_preferences_audit_metadata.py
0014_in_app_notifications_delivery.py
0015_incident_lifecycle_hardening.py
0016_form_f04_other_issue_description.py
```

آخرین Migration دیتابیس فعال:

```text
0016_form_f04_other_issue_description (head)
```

## ۲۱. فایل‌های مرجع

- `smart-building-backend/app/database.py`
- `smart-building-backend/app/config.py`
- `smart-building-backend/app/models/`
- `smart-building-backend/alembic/versions/`
- `smart-building-backend/alembic.ini`
- `smart-building-backend/compose.yaml`
- `smart-building-backend/compose.prod.example.yaml`
- `smart-building-backend/.env.example`
- `smart-building-backend/.env.production.example`

## ۲۲. نکات مهم نگهداری داده

- تاریخ‌ها در سطح اتصال دیتابیس با UTC مدیریت می‌شوند؛ نمایش شمسی و Timezone ایران مسئولیت لایه Frontend است.
- اطلاعات متغیر چک‌لیست و Snapshot در JSON ذخیره می‌شوند.
- فایل DWG در Storage و Metadata آن در PostgreSQL قرار می‌گیرد.
- Token و OTP خام ذخیره نمی‌شوند.
- تغییرات حساس در `audit_logs` ثبت می‌شوند.
- Snapshot تأییدشده با Hash محافظت می‌شود.
- حذف منطقی اعلان با `deleted_at` انجام می‌شود.
- ارتباط‌ها با Foreign Key و داده‌های پرتکرار با Index کنترل می‌شوند.

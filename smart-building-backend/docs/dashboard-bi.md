# BAMBO Dashboard و لایه BI

## API

تمام Endpointهای نمای کلی فقط خواندنی و زیر مسیر `/api/v1/dashboard` هستند:

`summary`، `pilots`، `my-actions` و بخش‌های `stages`، `gates`، `missions`،
`incidents`، `sla`، `forms`، `commercial` و `activities`.

پاسخ عمومی شامل `generated_at`، `filters`، `summary`، `items`، `pagination` و
`state` است. مقدار `state` یکی از `SUCCESS`، `PARTIAL_DATA`، `NO_DATA` یا
`NO_ACCESS` است (در نسخه فعلی برای داده ناقص هر بخش مقدار بخش‌ها در `summary`
حفظ می‌شود و `PARTIAL_DATA` در لایه مصرف‌کننده قابل استنتاج است).

## Scope و RLS

`SUPER_ADMIN` و کاربران دارای `dashboard.read_all` یا `pilots.read_all` همه
پایلوت‌ها را می‌بینند. نقش‌های عملیاتی مشترک، پرونده‌های حوزه کاری خود را
می‌بینند؛ نقش‌های محدود فقط پایلوت‌هایی را می‌بینند که در آن مأموریت، رخداد،
پیگیری مشتری، پیشنهاد تجاری یا F04 به کاربر تخصیص داده شده است. همین فیلتر قبل
از همه Queryهای جزئی اعمال می‌شود و شناسه خارج از Scope از API برنمی‌گردد.

برای Power BI، RLS باید در Semantic Model با جدول دسترسی زیر اعمال شود:

| user_id | role_name | pilot_id |
|---|---|---|
| شناسه کاربر | نقش فعال | شناسه پایلوت مجاز |

فیلتر پیشنهادی DAX: `Access[user_id] = VALUE(USERPRINCIPALNAME())` یا نگاشت
معادل در Gateway. Token، OTP، شماره موبایل خام و متن محرمانه رخداد وارد Factها
نمی‌شوند.

## مدل ستاره‌ای پیشنهادی

Factها از مدل‌های موجود خوانده می‌شوند و داده تکراری ذخیره نمی‌شود:

- `FactPilot`: Pilot، Project، وضعیت، مرحله فعلی و آخرین بروزرسانی
- `FactStage`: PilotStage و StageSubmission/Approval
- `FactMission`: Mission و وضعیت SLA
- `FactIncident`: Incident بدون description/evidence محرمانه
- `FactSLA`: موعد Mission/Incident و وضعیت محاسبه‌شده
- `FactCommercial`: CommercialProposal و FinalOutcome

ابعاد: Date، Pilot، Project، User/Role، Stage، Gate و Status. کلید‌های Fact به
کلید عددی رکوردهای موجود نگاشت می‌شوند. بروزرسانی افزایشی بر اساس
`updated_at`/`created_at` انجام شود.

Measureهای اصلی: Active Pilots، Completion Rate، SLA Compliance، Open Critical
Incidents، Stage Average Duration، First Approval Rate، Mission Completion Rate،
Upload Success Rate، Re-capture Rate، Customer Satisfaction، Pilot-to-Proposal
Rate و Proposal-to-Contract Rate.

اتصال Power BI باید فقط از Read Replica، Secure View یا Gateway انجام شود؛
اتصال مستقیم عمومی به Production DB مجاز نیست. Endpoint Embed فقط با
`reports.powerbi` و تنظیمات محیطی کار می‌کند و Secret در Frontend ذخیره نمی‌شود.

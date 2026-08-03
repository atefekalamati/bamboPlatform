# تحلیل فاصله فرانت گزارش‌های مدیریتی BAMBO

تاریخ بررسی: ۱۴۰۵/۰۵/۱۲

## وضعیت موجود

- صفحه «نمای کلی» عملیاتی است و از `dashboardService` و API واقعی استفاده می‌کند؛ بنابراین گزارش‌های مدیریتی باید به‌عنوان ماژول مستقل و مکمل داشبورد ساخته شوند، نه جایگزین آن.
- منوی «گزارش‌ها» وجود دارد اما غیرفعال است و Route/Page/Service ندارد.
- بک‌اند قرارداد کامل گزارش‌ها را در `/api/v1/reports` ارائه می‌کند: overview، pipeline، pilots، gates، actions، sla، kpis، incidents، one-page و external-evidence.
- پاسخ استاندارد شامل `summary`، `items`، `pagination` و stateهای `SUCCESS`، `PARTIAL_DATA`، `NO_DATA` و `NO_ACCESS` است.
- مجوزهای بک‌اند `reports.read`، `reports.sla` و `reports.kpi` هستند. Scope پرونده‌ها نیز در بک‌اند اعمال می‌شود.

## فاصله‌ها و اقدام لازم

| حوزه | وضعیت فعلی | اقدام فرانت |
|---|---|---|
| Navigation/Route | لینک غیرفعال | فعال‌سازی Permission-based و افزودن شش Route |
| API layer | فاقد Service گزارش | ساخت `reportService` با AbortSignal و Query استاندارد |
| فیلترها | وجود ندارد | فیلتر مشترک، همگام با URL، debounce و reset page |
| نمای مدیریتی | وجود ندارد | KPIهای بک‌اند، قیف، Gateها و اقدامات فوری |
| پیشرفت پرونده‌ها | وجود ندارد | جدول Server-side و Drill-down |
| اقدامات | وجود ندارد | فیلتر موعد/اولویت/نوع و لینک مستقیم |
| KPI/SLA | وجود ندارد | نمایش مقدار، هدف، نمونه و داده ناکافی بدون محاسبه Client |
| رخدادها | صفحه عملیاتی مستقل دارد | گزارش تجمیعی مستقل با Pagination سمت سرور |
| گزارش تک‌صفحه‌ای | وجود ندارد | صفحه تصمیم‌محور، شواهد و چاپ مرورگر |
| Stateها | وجود ندارد | Skeleton، Empty، No Access، Partial و Retry مستقل |
| Responsive/Print | وجود ندارد | جدول Card-like در موبایل و stylesheet چاپ |
| تست/مستندات | وجود ندارد | تست Service/URL/Permission و چهار سند تکمیلی |

## مرز مسئولیت

- محاسبه KPI، SLA، Gate، درصد پیشرفت و Scope فقط در بک‌اند باقی می‌ماند.
- فرانت صرفاً Query، نمایش و Drill-down را انجام می‌دهد.
- در صورت `PARTIAL_DATA` داده موجود نمایش داده می‌شود و هشدار محلی همان بخش نشان داده می‌شود.
- برای داده‌ای که endpoint ندارد مقدار حدسی یا Mock ساخته نمی‌شود.


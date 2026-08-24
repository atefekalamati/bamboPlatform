# تحلیل و پیاده‌سازی Refresh Token در فرانت‌اند BAMBO Pilot

تاریخ بررسی: ۱۴۰۵/۰۶/۰۲

نسخه مبنای فرانت‌اند: `b20d2f946c18790729a621693cffa64325884700`

قرارداد Backend مرجع: `350e91248c54cbeb8a6a5f96c20cd74c295417cf`

## خلاصه مشکل

Backend پس از تأیید OTP علاوه بر `access_token`، مقادیر `refresh_token`،
`expires_in` و `refresh_expires_in` را برمی‌گرداند و مسیر
`POST /auth/refresh` نیز Refresh Token را به‌صورت چرخشی تعویض می‌کند. فرانت‌اند
قبلی فقط Access Token و خلاصه کاربر را نگه می‌داشت؛ بنابراین پس از پایان عمر
Access Token، اولین پاسخ 401 کل Session را پاک می‌کرد و کاربر ناخواسته به صفحه
ورود بازمی‌گشت.

## نتیجه بررسی اولیه

| پرسش | وضعیت قبل از اصلاح |
|---|---|
| پاسخ Login | پاسخ کامل Backend دریافت می‌شد، اما فقط `access_token` و `user` مصرف می‌شدند. |
| محل Access Token | کلید `bambo_access_token` در `sessionStorage` |
| محل Refresh Token | ذخیره نمی‌شد. |
| حذف Refresh Token | عملاً هنگام Login دور انداخته می‌شد. |
| Interceptor | Axios در پروژه وجود ندارد؛ یک `httpClient` مبتنی بر Fetch وجود دارد. |
| مدیریت 401 | Session فوراً پاک و رویداد `bambo:auth-required` منتشر می‌شد. |
| استفاده از `/auth/refresh` | وجود نداشت. |
| Auth Context | Framework Context وجود ندارد؛ `sessionStore` و Bootstrap نقش Auth State را دارند. |
| Router Guard | Permission و کاربر جاری را از `sessionStore` می‌خواند. |

## قرارداد Backend

درخواست Refresh:

```http
POST /auth/refresh
Content-Type: application/json

{"refresh_token":"..."}
```

پاسخ موفق:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "expires_in": 900,
  "refresh_expires_in": 2592000,
  "user": {}
}
```

هر Refresh موفق، Refresh Token قبلی را باطل می‌کند. استفاده مجدد از Token قبلی
می‌تواند کل Session را باطل کند؛ به همین دلیل Single-flight بودن Refresh ضروری
است.

## Flow جدید

1. Login تمام Tokenها، زمان انقضا و خلاصه کاربر را ثبت می‌کند.
2. پیش از هر درخواست محافظت‌شده، انقضای Access Token با حاشیه ۶۰ ثانیه بررسی
   می‌شود.
3. اگر Token نزدیک انقضا باشد، ابتدا `/auth/refresh` فراخوانی می‌شود.
4. تمام درخواست‌های هم‌زمان منتظر یک Promise مشترک می‌مانند.
5. Tokenهای چرخش‌یافته به‌صورت یکپارچه جایگزین می‌شوند.
6. درخواست اصلی با Access Token جدید اجرا می‌شود.
7. اگر Backend به‌صورت غیرمنتظره 401 برگرداند، Refresh یک بار انجام و درخواست
   فقط یک بار Retry می‌شود.
8. اگر Refresh شکست بخورد، Session کامل پاک و Login فقط یک بار نمایش داده
   می‌شود.
9. Logout، Refresh Token را برای Revocation سمت سرور ارسال و سپس Storage را پاک
   می‌کند.

## مدیریت هم‌زمانی

`httpClient` یک `refreshPromise` مشترک دارد. علاوه بر آن، Token استفاده‌شده توسط
هر درخواست ثبت می‌شود. اگر درخواست دیگری در فاصله دریافت 401 قبلاً Token را
Refresh کرده باشد، درخواست دوم Refresh جدیدی ایجاد نمی‌کند و مستقیماً با Token
جدید Retry می‌شود. این رفتار از Rotation متوالی و باطل‌شدن Token تازه جلوگیری
می‌کند.

## Storage

اطلاعات زیر فقط در `sessionStorage` قرار می‌گیرند:

- `bambo_access_token`
- `bambo_refresh_token`
- `bambo_access_expires_at`
- `bambo_refresh_expires_at`
- `bambo_user_summary`

Business Data، فرم‌ها، پرونده‌ها، Permission Cache یا پاسخ Dashboard در Storage
ذخیره نمی‌شوند. `sessionStorage` با Reload صفحه حفظ می‌شود، ولی پس از بسته‌شدن
کامل Tab از بین می‌رود.

از آنجا که قرارداد فعلی Refresh Token را در JSON تحویل JavaScript می‌دهد،
نگهداری آن در Web Storage در برابر XSS مصون نیست. راهکار امن‌تر آینده، Refresh
Token در Cookie از نوع `HttpOnly + Secure + SameSite` همراه با CSRF Protection
است و به تغییر مشترک Backend و Frontend نیاز دارد.

## Bootstrap و UX

Bootstrap اکنون وجود Access Token یا Refresh Token را به‌عنوان Session قابل
بازیابی می‌شناسد. بنابراین Reload مرورگر در صورت وجود Refresh Token کاربر را
مستقیماً به Login برنمی‌گرداند. Refresh هیچ Loading سراسری نمایش نمی‌دهد و
درخواست‌های عادی پشت Promise مشترک منتظر می‌مانند.

دریافت HTML چاپ فرم‌ها نیز از Fetch مستقل خارج و وارد `httpClient` شد تا چاپ
فرم هنگام انقضای Access Token خراب نشود.

## تست‌های اضافه‌شده

- ذخیره Access و Refresh Token بعد از Login
- Refresh پیشگیرانه برای Access Token کوتاه‌عمر
- Retry یک‌باره درخواست 401
- Token Rotation
- سه درخواست هم‌زمان و فقط یک Refresh
- Refresh Token نامعتبر و Logout واقعی
- ارسال Refresh Token هنگام Logout برای Revocation
- جلوگیری از Loop در صورت 401 دوم
- ماندگاری Session Metadata پس از Reload
- پاک‌شدن کامل Session

## محدودیت Integration فعلی

در زمان این تغییر، `master` Backend هنوز قرارداد قدیمی بدون Refresh Token را
دارد. قرارداد Refresh در شاخه `agent/backend-mission-f03-operations` و commit
`350e912` موجود است. برای فعال‌شدن Flow در محیط واقعی، Migration شماره
`0020_refresh_tokens` و کدهای Auth همان شاخه باید ابتدا به Backend محیط مقصد
منتشر شوند. فرانت‌اند با پاسخ قدیمی Login همچنان اجرا می‌شود، اما تا Backend
Refresh را ارائه نکند Session طولانی‌مدت ایجاد نخواهد شد.

# تحلیل مسیر ارسال OTP و اشکالات Adapter آی‌پی‌پنل

تاریخ بررسی: ۱۴۰۵/۰۶/۰۱ (۲۰۲۶-۰۸-۲۳)
دامنه: فقط مسیر OTP و پیامک. بخش تماس/Astel خارج از دامنه است.

---

## ۱. نکته‌ای درباره ساختار فایل‌ها

فایل‌های زیر که در گزارش اولیه نام برده شده بودند **در این مخزن وجود ندارند**:

| فایل گزارش‌شده | معادل واقعی |
|---|---|
| `app/services/auth.py` | `app/services/security.py` |
| `app/services/otp.py` | `app/services/security.py` (تابع `request_otp` / `verify_otp`) |
| `app/routers/auth.py` | `app/routers/security.py` (`auth_router`) |
| `app/settings.py` | `app/config.py` |

منطق احراز هویت، OTP، نشست، RBAC و Audit همگی در یک ماژول `security` جمع شده‌اند.

---

## ۲. مسیر واقعی درخواست OTP

```
POST /auth/otp/request  { mobile }
  └─ app/routers/security.py :: otp_request_endpoint()          (خط ۱۴۷)
       └─ app/services/security.py :: request_otp()             (خط ۲۶۶)
            ├─ نرمال‌سازی شماره  → +989XXXXXXXXX
            ├─ قفل تراکنشی pg_advisory_xact_lock (شماره + IP)
            ├─ بررسی Rate Limit و Cooldown
            ├─ تولید کد        → secrets.randbelow(1_000_000)
            ├─ get_sms_provider().send_otp(...)                 ← نقطه اتصال به Provider
            ├─ INSERT otp_requests (code_hash, provider_status, ...)
            ├─ INSERT audit_logs  (auth.otp_requested)
            └─ اگر delivery.accepted نبود → status='failed' + خطای ۵۰۳
```

---

## ۳. پاسخ به پرسش‌های بررسی

### ۳.۱ کد OTP کجا تولید می‌شود؟

`app/services/security.py:299`

```python
code = f"{secrets.randbelow(1_000_000):06d}"
```

شش رقم، با مولد اعداد تصادفی رمزنگاری‌شده (`secrets`). درست است.

### ۳.۲ آیا OTP قبل از ارسال ذخیره می‌شود؟

**خیر — بعد از ارسال ذخیره می‌شود.** ترتیب فعلی:

1. تولید کد
2. `send_otp(...)` ← فراخوانی شبکه
3. ساخت رکورد `OtpRequest` و `db.commit()`

این ترتیب یک پیامد دارد: اگر پروسه دقیقاً بین مرحله ۲ و ۳ کرش کند، پیامک رفته ولی رکوردی وجود ندارد؛ کاربر کدی دریافت می‌کند که قابل استفاده نیست. پیامد امنیتی ندارد (fail-closed است) ولی تجربه کاربری بدی می‌سازد.

### ۳.۳ آیا مقدار OTP به Provider منتقل می‌شود؟

**اینجا ریشه باگ است.**

سرویس، کد را در قالب متن آماده به Provider می‌دهد:

```python
delivery = get_sms_provider().send_otp(
    mobile=mobile,
    purpose="auth",
    body=f"کد ورود BAMBO: {code}",   # ← کد اینجاست
)
```

اما `IpPanelSmsProvider.send_otp` پارامتر `body` را **کاملاً نادیده می‌گیرد**:

```python
def send_otp(self, *, mobile: str, purpose: str, body: str) -> SmsSendResult:
    return self._send_pattern(mobile=mobile, reference=purpose)
    #                                        ^^^^^^^^^^^^^^^^^ body دور ریخته می‌شود
```

و `_send_pattern` این Payload را می‌سازد:

```python
payload = json.dumps({
    "sending_type": "pattern",
    "from_number": self.sender,
    "code": self.pattern_code,     # ← این «شناسه الگو» است، نه کد ورود
    "recipients": [mobile],
})
```

فیلد `code` در سطح ریشه، طبق مستندات آی‌پی‌پنل، **شناسه Pattern** است. مقدار متغیرهای الگو باید در یک شیء جداگانه به‌نام `params` بیاید که در Payload فعلی **اصلاً وجود ندارد**.

> **نتیجه: کد ورود هرگز از سرور خارج نمی‌شود.**

### ۳.۴ Template ID چگونه خوانده می‌شود؟

`os.environ["SMS_TEMPLATE_ID"]` در `__init__`. اگر تنظیم نشده باشد `KeyError` می‌دهد که در `get_sms_provider()` گرفته شده و به `UnconfiguredSmsProvider` تبدیل می‌شود (Fail-Closed درست).

مشکل: **یک شناسه واحد برای هر دو نوع پیام.** هم `send_otp` و هم `send_notification` از `self.pattern_code` استفاده می‌کنند. PRD بند ۸.۳ صراحتاً «Templateهای جدا برای Auth و Notification» خواسته است.

### ۳.۵ Payload نهایی ارسال‌شده به آی‌پی‌پنل چیست؟

**فعلی (خراب):**

```json
{
  "sending_type": "pattern",
  "from_number": "+983000505",
  "code": "spuueljew7dxi3z",
  "recipients": ["+989121234567"]
}
```

**قرارداد رسمی آی‌پی‌پنل:**

```json
{
  "sending_type": "pattern",
  "from_number": "+983000505",
  "code": "spuueljew7dxi3z",
  "recipients": ["+989121234567"],
  "params": { "code": "123456" }
}
```

بلوک `params` غایب است.

### ۳.۶ آیا از Pattern SMS استفاده می‌شود یا Text SMS؟

Pattern (`sending_type: "pattern"`). این انتخاب برای ایران درست است چون ارسال متن آزاد به شماره‌های غیرعضو محدودیت دارد.

### ۳.۷ Placeholderهای Template چگونه مقداردهی می‌شوند؟

**هیچ‌جا.** مکانیزمی برای مقداردهی متغیرهای الگو در کد وجود ندارد.

---

## ۴. اشکالات یافت‌شده

### 🔴 B-1 — مقدار OTP در Payload نیست

شرح در بند ۳.۳. **اثر: هیچ‌کس نمی‌تواند وارد شود.**

### 🔴 B-2 — موفقیت جعلی (Fake Success)

`accepted` فقط بر اساس کد وضعیت HTTP تعیین می‌شود:

```python
accepted = 200 <= response.status < 300
```

اما آی‌پی‌پنل می‌تواند **HTTP 200 با `meta.status: false`** برگرداند (مثلاً اعتبار ناکافی، الگوی غیرفعال، متغیر ناقص). در آن حالت سیستم پیام را «ارسال‌شده» ثبت می‌کند در حالی که ارسال نشده.

پاسخ واقعی موفق:

```json
{"data": {"message_outbox_ids": [1123594208]},
 "meta": {"status": true, "message": "انجام شد", "message_code": "200-1"}}
```

پاسخ واقعی ناموفق:

```json
{"data": null,
 "meta": {"status": false, "message": "...", "message_code": "400-1", "errors": {}}}
```

### 🔴 B-3 — شناسه پیام اشتباه استخراج می‌شود

کد فعلی دنبال این کلیدها می‌گردد:

```python
data.get("message_id") or data.get("id") or data.get("bulk_id")
or data.get("tracking_code") or data["data"].get("message_id")
```

هیچ‌کدام در پاسخ آی‌پی‌پنل وجود ندارند. شناسه واقعی در `data.message_outbox_ids[0]` است. در نتیجه `message_id` همیشه `None` می‌شود و به مقدار جایگزین می‌افتد:

```python
provider_message_id=str(message_id or reference)   # reference == "auth"
```

یعنی در ستون `otp_requests.provider_message_id` رشته ثابت **`"auth"`** ذخیره می‌شود — پیگیری تحویل پیامک عملاً غیرممکن است.

### 🟡 B-4 — `provider_status` از فیلد اشتباه خوانده می‌شود

`data.get("status")` در سطح ریشه خوانده می‌شود، در حالی که وضعیت واقعی در `meta.status` و کد آن در `meta.message_code` است.

### 🟡 B-5 — یک Template برای Auth و Notification

مغایر با PRD بند ۸.۳.

### 🟡 B-6 — بدون Retry

بند «Retry کنترل‌شده» در PRD آمده ولی پیاده نشده. خطاهای گذرای شبکه بلافاصله به شکست تبدیل می‌شوند.

### 🟢 B-7 — نام متغیر Timeout غیراستاندارد

`SMS_TIMEOUT_SECONDS` استفاده شده، در حالی که استاندارد تیم `SMS_TIMEOUT` است.

---

## ۵. بررسی امنیتی (وضعیت فعلی)

| الزام | وضعیت | محل |
|---|---|---|
| OTP به‌صورت Plain Text ذخیره نشود | ✅ HMAC-SHA256 با `AUTH_SECRET` و Salt از `public_id` | `security.py:126` |
| مقایسه مقاوم در برابر Timing Attack | ✅ `hmac.compare_digest` | `security.py:399` |
| Rate Limit | ✅ ۳ درخواست / ۱۰ دقیقه بر شماره، ۲۰ بر IP | `security.py:270` |
| Cooldown ارسال مجدد | ✅ ۶۰ ثانیه | `security.py:290` |
| محدودیت تعداد تلاش | ✅ ۵ بار، سپس `status='locked'` | `security.py:400` |
| انقضا | ✅ ۳۰۰ ثانیه، `status='expired'` | `security.py:390` |
| عدم استفاده مجدد | ✅ فقط `status='pending'` پذیرفته می‌شود | `security.py:385` |
| OTP در لاگ ثبت نشود | ✅ در هیچ لاگ یا Audit ثبت نمی‌شود | — |
| شماره کامل در لاگ نباشد | ✅ `mask_mobile()` → `+989***4567` | `security.py:44` |
| عدم افشای وجود حساب | ✅ خطای عمومی یکسان `OTP_INVALID` | `security.py:378` |

**لایه امنیتی OTP سالم است و نیازی به تغییر ندارد.** تنها استثنا: در `APP_ENV` برابر `development` یا `test`، کد خام در فیلد `debug_code` پاسخ API برگردانده می‌شود که رفتاری عمدی و محدود به محیط غیرتولیدی است.

---

## ۶. جمع‌بندی

| # | اشکال | شدت |
|---|---|---|
| B-1 | مقدار OTP در Payload ارسال نمی‌شود | 🔴 مسدودکننده |
| B-2 | موفقیت جعلی وقتی `meta.status = false` | 🔴 مسدودکننده |
| B-3 | استخراج اشتباه شناسه پیام | 🔴 بالا |
| B-4 | خواندن `provider_status` از فیلد اشتباه | 🟡 متوسط |
| B-5 | یک Template برای Auth و Notification | 🟡 متوسط |
| B-6 | نبود Retry | 🟡 متوسط |
| B-7 | نام‌گذاری غیراستاندارد Timeout | 🟢 کم |

منبع قرارداد: [IPPanel Edge API — Send Pattern SMS](https://ippanelcom.github.io/Edge-Document/docs/send/pattern)

# BAMBO call integration

The call domain is provider-neutral. Development and tests use `CALL_PROVIDER=mock`.
Production deliberately fails readiness until Astel supplies its official OpenAPI/Postman
contract, authentication scheme, outbound-call request/response samples, status mapping,
webhook payload, replay window, signature algorithm, retry/rate-limit rules, and recording
retrieval/retention rules. No Astel URL or header has been guessed.

## Stage policy matrix

| Stage | Exact title | Call use | Required | Allowed role | Source |
|---:|---|---|---|---|---|
| 1 | انتخاب پروژه مناسب برای پایلوت | none | no | sales | PRD stage 1 |
| 2 | معرفی و موافقت | initial coordination and contact confirmation | optional | sales, support | PRD G1/F01 |
| 3 | دریافت DWG و اطلاعات طبقات | document exchange only | no | setup | PRD stage 3 |
| 4 | راه‌اندازی در پلتفرم اصلی | internal setup | no | setup | PRD stage 4 |
| 5 | برنامه‌ریزی و تخصیص مأموریت | schedule/site coordination | optional | operations | PRD mission fields |
| 6 | آمادگی قبل از برداشت | checklist | no | capture expert | PRD stage 6 |
| 7 | اجرای برداشت طبقات | field execution | no | capture expert | PRD stage 7 |
| 8 | کنترل نتیجه چندطبقه | status resolution | no | capture expert | PRD stage 8 |
| 9 | وضعیت Upload در پلتفرم اصلی | upload confirmation | no | operations | PRD stage 9 |
| 10 | کنترل پردازش در پلتفرم اصلی | technical processing | no | technical | PRD stage 10 |
| 11 | اطلاع‌رسانی آماده‌شدن بازدید | fallback when delivery fails | optional | support | PRD stage 11 |
| 12 | آموزش اولیه مالک | training | no | support | PRD stage 12 |
| 13 | پیگیری موفقیت مشتری | customer-success follow-up | optional | customer success, support | PRD F04 |
| 14 | ادامه برداشت‌های پایلوت | uses new mission cycle | no direct policy | operations | PRD stage 14 |
| 15 | ارزیابی موفقیت پایلوت | evaluation | no | pilot manager | PRD stage 15 |
| 16 | جلسه جمع‌بندی با مالک | confirm decision/blocker | optional | customer success, sales | PRD stage 16 |
| 17 | تهیه و ارائه پیشنهاد تجاری | proposal delivery | no | sales | PRD stage 17 |
| 18 | پیگیری تا تصمیم و عقد قرارداد | commercial decision follow-up | required | sales, pilot manager | PRD stage 18 |
| 19 | تبدیل پایلوت به قرارداد یا بستن پرونده | final recorded decision | no | pilot manager | PRD stage 19 |

Stage 18 requires at least one answered/completed call, a business outcome and summary.
An answered call alone is insufficient. A manager override is audited and requires a reason.

## Mock webhook

In non-production environments set `CALL_PROVIDER=mock` and optionally
`MOCK_CALL_WEBHOOK_SECRET`. Sign the exact JSON request bytes with HMAC-SHA256 and send the
hex digest in `X-Call-Signature`. This mock contract is test-only and is not an Astel claim.

Full destination numbers and recording references are never returned in ordinary call APIs.
Recording references require `calls.recording.read`. Database backup and recording retention
must follow the deployment privacy policy before recording is enabled.

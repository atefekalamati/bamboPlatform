# تعریف KPIهای گزارش

| کلید | صورت/مخرج | هدف | نبود نمونه |
|---|---|---|---|
| floors_completed_on_plan_percent | Floor با capture_state=completed / MissionFloor | >=95% | insufficient_data |
| successful_upload_percent | main_upload_completed / MissionFloor | >=98% | insufficient_data |
| recapture_percent | capture_state=needs_revision / MissionFloor | <=5% | insufficient_data |
| correct_floor_assignment_percent | correct_floor_link / MissionFloor | >=99% | insufficient_data |
| successful_notification_percent | Notification delivered / Notification | >=95% | insufficient_data |
| successful_training_percent | F04 training_completed / F04 | >=90% | insufficient_data |
| average_satisfaction_score | میانگین satisfaction_score ثبت‌شده | >=8/10 | insufficient_data |
| continuation_interest_percent | true / پاسخ‌های non-null | >=70% | insufficient_data |
| proposal_ready_percent | true / پاسخ‌های non-null | >=60% | insufficient_data |

تمام درصدها در بازه 0 تا 100 محدود می‌شوند. صفر نمونه هرگز به‌عنوان KPI صفر گزارش نمی‌شود. KPIهایی که داده عملیاتی قابل اتکا ندارند در API جعل نشده و در Gap Analysis باقی مانده‌اند.

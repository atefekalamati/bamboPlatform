# منابع داده گزارش‌ها

| حوزه | مدل مرجع | فیلدهای کلیدی |
|---|---|---|
| پرونده | Pilot/Project/Owner | status، current_stage، updated_at |
| فرایند | PilotStage/StageSubmission/StageApproval/PilotGate | status، approved_at، reviewer |
| عملیات | Mission/MissionFloor/FormF03 | SLA، capture_state، upload، floor link |
| مشتری | FormF04/Notification | training، satisfaction، continuation، delivery |
| رخداد | Incident | severity، type، owner، response_due_at، status |
| ارزیابی | PilotEvaluation | وضعیت پنج‌بعدی و one_page_summary ثبت‌شده |
| تجاری | CommercialProposal/CustomerFollowUp/FinalOutcome | follow_up_at، outcome، approval |
| شواهد خارجی | ExternalEvidenceCheck | capability، status، checker، checked_at، short result |

هیچ Fact یا Snapshot جدیدی ذخیره نمی‌شود. OTP، Token، شماره موبایل، payload کامل پلتفرم اصلی، فایل صوتی، سری زمانی یا شرح کامل حساس Incident وارد گزارش خلاصه نمی‌شود. زمان‌ها از Backend به UTC بازگردانده می‌شوند.

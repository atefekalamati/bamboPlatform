import { sessionStore } from "../app/sessionStore.js";
import { notificationLabels } from "../components/NotificationCenter.js";
import { notificationService } from "../services/notificationService.js";

const node = (tag, className = "", text = "") => { const item = document.createElement(tag); item.className = className; item.textContent = text; return item; };
const toggle = (labelText, description = "") => {
  const label = node("label", "notification-preference");
  const input = document.createElement("input");
  input.type = "checkbox";
  const copy = node("span", "notification-preference__copy");
  copy.append(node("strong", "", labelText), node("small", "", description));
  label.append(input, copy);
  return { label, input };
};

export const NotificationPreferencesPage = () => {
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canRead = permissions.includes("notifications.read");
  const canManage = permissions.includes("notifications.manage_preferences");
  const page = node("div", "page notification-settings-page");
  const heading = node("header", "page-heading");
  heading.append(node("p", "page-heading__eyebrow", "تنظیمات شخصی"), node("h1", "page-heading__title", "تنظیمات اعلان‌ها"), node("p", "page-heading__description", "کانال‌های اعلان را مدیریت کنید. OTP فقط برای احراز هویت است و از پیامک عملیاتی جداست."));
  const content = node("div", "notification-settings card");
  page.append(heading, content);
  if (!canRead) { content.append(node("p", "error-state__message", "برای مشاهده تنظیمات اعلان دسترسی ندارید.")); return page; }

  const load = async () => {
    content.replaceChildren(node("p", "loading-state", "در حال دریافت تنظیمات…"));
    try {
      const preferences = await notificationService.getPreferences();
      const form = node("form", "notification-preferences-form");
      const inApp = toggle("اعلان درون‌برنامه‌ای", "نمایش اعلان‌ها در مرکز اعلان BAMBO");
      const sms = toggle("پیامک عملیاتی", "اعلان‌های انتخاب‌شده به شماره ثبت‌شده شما نیز پیامک می‌شوند.");
      const critical = toggle("پیامک اعلان‌های بحرانی", "برای حفظ ایمنی و پیگیری رخدادهای حساس توصیه می‌شود فعال بماند.");
      inApp.input.checked = preferences.in_app_enabled;
      sms.input.checked = preferences.sms_enabled;
      critical.input.checked = preferences.critical_sms_enabled;
      const categories = node("fieldset", "notification-category-settings");
      categories.append(node("legend", "", "دسته‌های پیامک"));
      const categoryInputs = {};
      Object.entries(notificationLabels.categories).forEach(([code, label]) => {
        const option = toggle(label);
        option.input.checked = preferences.sms_categories?.[code] ?? true;
        categoryInputs[code] = option.input;
        categories.append(option.label);
      });
      const hours = node("div", "notification-quiet-hours");
      const start = document.createElement("input");
      const end = document.createElement("input");
      start.type = end.type = "time";
      start.className = end.className = "form-field__input";
      start.value = preferences.quiet_hours_start ?? "";
      end.value = preferences.quiet_hours_end ?? "";
      const startLabel = node("label", "form-field"); startLabel.append(node("span", "form-field__label", "شروع ساعات سکوت"), start);
      const endLabel = node("label", "form-field"); endLabel.append(node("span", "form-field__label", "پایان ساعات سکوت"), end);
      hours.append(startLabel, endLabel);
      const feedback = node("p", "form-feedback");
      const save = node("button", "button button--primary", "ذخیره تنظیمات"); save.type = "submit";
      [...form.querySelectorAll("input")].forEach((input) => { input.disabled = !canManage; });
      form.append(inApp.label, sms.label, critical.label, categories, hours, feedback);
      if (canManage) form.append(save); else form.append(node("p", "muted-text", "این تنظیمات برای نقش شما فقط خواندنی است."));
      form.querySelectorAll("input").forEach((input) => { input.disabled = !canManage; });
      form.addEventListener("submit", async (event) => {
        event.preventDefault(); save.disabled = true; save.textContent = "در حال ذخیره…"; feedback.textContent = "";
        const payload = {
          in_app_enabled: inApp.input.checked, sms_enabled: sms.input.checked,
          critical_sms_enabled: critical.input.checked,
          sms_categories: Object.fromEntries(Object.entries(categoryInputs).map(([code, input]) => [code, input.checked])),
          quiet_hours_start: start.value || null, quiet_hours_end: end.value || null,
        };
        try { await notificationService.updatePreferences(payload); feedback.textContent = "تنظیمات ذخیره شد."; feedback.dataset.type = "success"; }
        catch (error) { feedback.textContent = error.message ?? "ذخیره تنظیمات انجام نشد."; feedback.dataset.type = "error"; }
        finally { save.disabled = false; save.textContent = "ذخیره تنظیمات"; }
      });
      content.replaceChildren(form);
    } catch (error) { const retry = node("button", "button button--primary", "تلاش مجدد"); retry.type = "button"; retry.addEventListener("click", load); content.replaceChildren(node("p", "error-state__message", error.message ?? "دریافت تنظیمات انجام نشد."), retry); }
  };
  load();
  return page;
};

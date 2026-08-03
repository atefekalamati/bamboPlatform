import {
  PERSIAN_MONTHS, PERSIAN_WEEKDAYS, formatJalaliDateInput, formatJalaliDateTimeInput,
  formatJalaliManualInput, getIranJalaliParts, jalaliMonthLength, jalaliWeekdayIndex,
  parseJalaliDateInput, parseJalaliDateTimeInput, toLatinDigits, toPersianDigits,
} from "../utils/jalaliDateTime.js";

const nativeValue = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value");
let openPicker = null;
const pad = (value) => String(value).padStart(2, "0");

const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

const cursorAfterDigits = (text, count) => {
  if (!count) return 0;
  let seen = 0;
  for (let index = 0; index < text.length; index += 1) {
    if (/\d/.test(toLatinDigits(text[index]))) seen += 1;
    if (seen === count) return index + 1;
  }
  return text.length;
};

class PersianDatePicker {
  constructor(input) {
    this.input = input;
    this.originalType = input.type;
    this.dateTime = this.originalType === "datetime-local";
    this.required = input.required;
    this.minimum = input.min;
    this.maximum = input.max;
    this.initialValue = nativeValue.get.call(input);
    this.today = getIranJalaliParts();
    this.view = { year: this.today.year, month: this.today.month };
    this.build();
    this.setApiValue(this.initialValue);
    this.bind();
  }

  build() {
    const input = this.input;
    input.type = "text";
    input.dataset.jalaliEnhanced = "true";
    input.dataset.jalaliMode = this.dateTime ? "datetime" : "date";
    input.dataset.dateTimezone = "Asia/Tehran";
    input.inputMode = "numeric";
    input.autocomplete = "off";
    input.placeholder = this.dateTime ? "۱۴۰۵/۰۵/۱۲ ۱۴:۳۰" : "۱۴۰۵/۰۵/۱۲";
    this.wrapper = element("div", "persian-date-picker");
    input.parentNode.insertBefore(this.wrapper, input);
    this.wrapper.append(input);
    this.trigger = element("button", "persian-date-picker__trigger");
    this.trigger.type = "button";
    this.trigger.setAttribute("aria-label", "باز کردن تقویم شمسی");
    this.trigger.setAttribute("aria-haspopup", "dialog");
    this.trigger.innerHTML = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 2v4M18 2v4M3 9h18M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z"/></svg>';
    this.wrapper.append(this.trigger);
    this.popover = element("section", "persian-date-picker__popover");
    this.popover.hidden = true;
    this.popover.dir = "rtl";
    this.popover.setAttribute("role", "dialog");
    this.popover.setAttribute("aria-modal", "false");
    this.popover.setAttribute("aria-label", this.dateTime ? "انتخاب تاریخ و زمان شمسی" : "انتخاب تاریخ شمسی");
    this.backdrop = element("button", "persian-date-picker__backdrop");
    this.backdrop.type = "button";
    this.backdrop.hidden = true;
    this.backdrop.setAttribute("aria-label", "بستن تقویم");
    this.wrapper.append(this.backdrop, this.popover);
    this.render();
    this.trigger.disabled = input.disabled || input.readOnly;
  }

  bind() {
    Object.defineProperty(this.input, "value", {
      configurable: true,
      get: () => this.apiValue(),
      set: (value) => this.setApiValue(value),
    });
    this.input.addEventListener("focus", () => this.open());
    this.input.addEventListener("input", () => this.onManualInput());
    this.input.addEventListener("blur", () => window.setTimeout(() => this.validate(), 0));
    this.input.addEventListener("keydown", (event) => { if (event.key === "ArrowDown" && event.altKey) { event.preventDefault(); this.open(); } });
    this.trigger.addEventListener("click", () => this.popover.hidden ? this.open() : this.close());
    this.backdrop.addEventListener("click", () => this.close());
    this.popover.addEventListener("keydown", (event) => this.onPopoverKeydown(event));
    this.input.form?.addEventListener("reset", () => window.setTimeout(() => this.setApiValue(this.input.defaultValue), 0));
  }

  visibleValue() { return nativeValue.get.call(this.input); }
  parser() { return this.dateTime ? parseJalaliDateTimeInput : parseJalaliDateInput; }
  formatter() { return this.dateTime ? formatJalaliDateTimeInput : formatJalaliDateInput; }
  apiValue() { const value = this.visibleValue(); return value.trim() ? this.parser()(value) ?? "" : ""; }
  setApiValue(value) { nativeValue.set.call(this.input, this.formatter()(value)); this.input.setCustomValidity(""); this.syncView(); }

  syncView() {
    const match = toLatinDigits(this.visibleValue()).match(/^(\d{4})\/(\d{2})\/(\d{2})/);
    if (match) this.view = { year: +match[1], month: +match[2] };
  }

  onManualInput() {
    const raw = this.visibleValue();
    const caret = this.input.selectionStart ?? raw.length;
    const digitCount = toLatinDigits(raw.slice(0, caret)).replace(/\D/g, "").length;
    const formatted = formatJalaliManualInput(raw, this.dateTime);
    nativeValue.set.call(this.input, formatted);
    const nextCaret = cursorAfterDigits(formatted, digitCount);
    this.input.setSelectionRange(nextCaret, nextCaret);
    this.input.setCustomValidity("");
    this.syncView();
    if (!this.popover.hidden) this.render();
  }

  validate() {
    const value = this.visibleValue().trim();
    if (!value) { this.input.setCustomValidity(""); return true; }
    const parsed = this.parser()(value);
    const valid = parsed && this.inRange(parsed);
    this.input.setCustomValidity(valid ? "" : this.dateTime
      ? "تاریخ و زمان شمسی معتبر وارد کنید."
      : "تاریخ شمسی معتبر وارد کنید.");
    if (valid) nativeValue.set.call(this.input, this.formatter()(parsed));
    return Boolean(valid);
  }

  inRange(value) {
    const comparable = this.dateTime ? new Date(value).getTime() : value;
    const boundary = (raw) => this.dateTime
      ? new Date(parseJalaliDateTimeInput(formatJalaliDateTimeInput(raw))).getTime()
      : raw;
    const min = this.minimum ? boundary(this.minimum) : null;
    const max = this.maximum ? boundary(this.maximum) : null;
    return (min === null || comparable >= min) && (max === null || comparable <= max);
  }

  open() {
    if (this.input.disabled || this.input.readOnly) return;
    if (openPicker && openPicker !== this) openPicker.close();
    openPicker = this;
    this.syncView(); this.render();
    this.popover.hidden = false; this.backdrop.hidden = false;
    this.trigger.setAttribute("aria-expanded", "true");
  }

  close(returnFocus = false) {
    this.popover.hidden = true; this.backdrop.hidden = true;
    this.trigger.setAttribute("aria-expanded", "false");
    if (openPicker === this) openPicker = null;
    if (returnFocus) this.input.focus();
  }

  moveMonth(offset) {
    let month = this.view.month + offset;
    let year = this.view.year;
    if (month < 1) { month = 12; year -= 1; }
    if (month > 12) { month = 1; year += 1; }
    this.view = { year, month }; this.render();
  }

  selectedParts() {
    const match = toLatinDigits(this.visibleValue()).match(/^(\d{4})\/(\d{2})\/(\d{2})(?:\s+(\d{2}):(\d{2}))?/);
    return match ? { year: +match[1], month: +match[2], day: +match[3], hour: +(match[4] ?? this.today.hour), minute: +(match[5] ?? this.today.minute) } : null;
  }

  selectDay(day) {
    const selected = this.selectedParts();
    const hour = this.hourSelect ? this.hourSelect.value : selected?.hour ?? this.today.hour;
    const minute = this.minuteSelect ? this.minuteSelect.value : selected?.minute ?? this.today.minute;
    const visible = `${this.view.year}/${String(this.view.month).padStart(2, "0")}/${String(day).padStart(2, "0")}${this.dateTime ? ` ${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}` : ""}`;
    const parsed = this.parser()(visible);
    if (!parsed || !this.inRange(parsed)) return;
    nativeValue.set.call(this.input, this.formatter()(parsed));
    this.input.setCustomValidity("");
    this.input.dispatchEvent(new Event("input", { bubbles: true }));
    this.input.dispatchEvent(new Event("change", { bubbles: true }));
    this.close(true);
  }

  render() {
    const selected = this.selectedParts();
    const header = element("header", "persian-date-picker__header");
    const previous = element("button", "persian-date-picker__nav", "‹"); previous.type = "button"; previous.setAttribute("aria-label", "ماه قبل"); previous.onclick = () => this.moveMonth(-1);
    const next = element("button", "persian-date-picker__nav", "›"); next.type = "button"; next.setAttribute("aria-label", "ماه بعد"); next.onclick = () => this.moveMonth(1);
    const month = element("select", "persian-date-picker__select"); month.setAttribute("aria-label", "ماه");
    PERSIAN_MONTHS.forEach((name, index) => { const option = new Option(name, String(index + 1), false, index + 1 === this.view.month); month.add(option); });
    month.onchange = () => { this.view.month = +month.value; this.render(); };
    const year = element("input", "persian-date-picker__year"); year.type = "number"; year.min = "1200"; year.max = "1600"; year.value = String(this.view.year); year.setAttribute("aria-label", "سال");
    year.onchange = () => { const value = Math.max(1200, Math.min(1600, +year.value || this.today.year)); this.view.year = value; this.render(); };
    header.append(next, month, year, previous);
    const grid = element("div", "persian-date-picker__grid"); grid.setAttribute("role", "grid");
    PERSIAN_WEEKDAYS.forEach((name) => { const weekday = element("span", "persian-date-picker__weekday", name); weekday.setAttribute("role", "columnheader"); grid.append(weekday); });
    const offset = jalaliWeekdayIndex(this.view.year, this.view.month);
    for (let index = 0; index < offset; index += 1) grid.append(element("span", "persian-date-picker__empty"));
    for (let day = 1; day <= jalaliMonthLength(this.view.year, this.view.month); day += 1) {
      const button = element("button", "persian-date-picker__day", toPersianDigits(day)); button.type = "button"; button.dataset.day = String(day); button.setAttribute("role", "gridcell");
      const isToday = this.view.year === this.today.year && this.view.month === this.today.month && day === this.today.day;
      const isSelected = selected?.year === this.view.year && selected?.month === this.view.month && selected?.day === day;
      if (isToday) { button.classList.add("is-today"); button.setAttribute("aria-current", "date"); }
      if (isSelected) { button.classList.add("is-selected"); button.setAttribute("aria-selected", "true"); }
      const candidate = this.dateTime
        ? parseJalaliDateTimeInput(`${this.view.year}/${this.view.month}/${day} ${pad(selected?.hour ?? 12)}:${pad(selected?.minute ?? 0)}`)
        : parseJalaliDateInput(`${this.view.year}/${this.view.month}/${day}`);
      if (!candidate || !this.inRange(candidate)) button.disabled = true;
      button.onclick = () => this.selectDay(day); grid.append(button);
    }
    const footer = element("footer", "persian-date-picker__footer");
    if (this.dateTime) {
      const time = element("div", "persian-date-picker__time");
      this.hourSelect = element("select", "persian-date-picker__select"); this.hourSelect.setAttribute("aria-label", "ساعت");
      this.minuteSelect = element("select", "persian-date-picker__select"); this.minuteSelect.setAttribute("aria-label", "دقیقه");
      for (let hour = 0; hour < 24; hour += 1) this.hourSelect.add(new Option(toPersianDigits(pad(hour)), String(hour), false, hour === (selected?.hour ?? this.today.hour)));
      for (let minute = 0; minute < 60; minute += 1) this.minuteSelect.add(new Option(toPersianDigits(pad(minute)), String(minute), false, minute === (selected?.minute ?? this.today.minute)));
      time.append(this.hourSelect, element("span", "persian-date-picker__time-separator", ":"), this.minuteSelect); footer.append(time);
    }
    const actions = element("div", "persian-date-picker__actions");
    const today = element("button", "button button--ghost", "امروز"); today.type = "button"; today.onclick = () => { this.view = { year: this.today.year, month: this.today.month }; this.render(); this.selectDay(this.today.day); };
    actions.append(today);
    if (!this.required) { const clear = element("button", "button button--ghost", "پاک‌کردن"); clear.type = "button"; clear.onclick = () => { nativeValue.set.call(this.input, ""); this.input.setCustomValidity(""); this.input.dispatchEvent(new Event("change", { bubbles: true })); this.close(true); }; actions.append(clear); }
    footer.append(actions);
    this.popover.replaceChildren(header, grid, footer);
  }

  onPopoverKeydown(event) {
    if (event.key === "Escape") { event.preventDefault(); this.close(true); return; }
    const day = event.target.closest?.("[data-day]");
    if (day && ["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(event.key)) {
      event.preventDefault();
      const delta = { ArrowLeft: 1, ArrowRight: -1, ArrowUp: -7, ArrowDown: 7 }[event.key];
      const target = this.popover.querySelector(`[data-day="${+day.dataset.day + delta}"]:not(:disabled)`);
      target?.focus();
    }
    if (event.key === "Tab" && matchMedia("(max-width: 48rem)").matches) {
      const focusable = [...this.popover.querySelectorAll("button:not(:disabled), select, input")];
      if (!focusable.length) return;
      if (event.shiftKey && document.activeElement === focusable[0]) { event.preventDefault(); focusable.at(-1).focus(); }
      else if (!event.shiftKey && document.activeElement === focusable.at(-1)) { event.preventDefault(); focusable[0].focus(); }
    }
  }
}

const enhance = (input) => {
  if (input.dataset.jalaliEnhanced === "true" || !["date", "datetime-local"].includes(input.type)) return;
  input._persianDatePicker = new PersianDatePicker(input);
};

export const enhancePersianDatePickers = (root = document) => {
  if (root instanceof HTMLInputElement) enhance(root);
  root.querySelectorAll?.('input[type="date"], input[type="datetime-local"]').forEach(enhance);
};

export const startPersianDatePickers = (root = document.documentElement) => {
  enhancePersianDatePickers(root);
  const observer = new MutationObserver((mutations) => mutations.forEach(({ addedNodes }) => addedNodes.forEach((node) => {
    if (node instanceof Element) enhancePersianDatePickers(node);
  })));
  observer.observe(root, { childList: true, subtree: true });
  document.addEventListener("pointerdown", (event) => {
    if (openPicker && !openPicker.wrapper.contains(event.target)) openPicker.close();
  });
  return () => observer.disconnect();
};

export { PersianDatePicker };

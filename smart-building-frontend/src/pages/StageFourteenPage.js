import { sessionStore } from "../app/sessionStore.js";
import {
  StageReviewPanel,
  StageSnapshots,
  stageElement as element,
} from "../components/StageShared.js";
import { dwgService } from "../services/dwgService.js";
import { evaluationService } from "../services/evaluationService.js";
import { missionService } from "../services/missionService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { formatPersianDate } from "../utils/dateFormatter.js";

const STATUS_LABELS = Object.freeze({
  open: "باز",
  submitted: "در انتظار بررسی",
  approved: "تأییدشده",
  needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده",
});

const RECHECKS = Object.freeze([
  [5, "مأموریت جدید با تاریخ، مسئول و طبقات مشخص صادر و دریافت آن تأیید شد."],
  [6, "آمادگی ایمنی، تجهیزات، پروژه، طبقه و Plan پیش از برداشت کنترل شد."],
  [7, "برداشت هر طبقه با مسیر پیوسته، پایدار و پوشش قسمت‌های اصلی انجام شد."],
  [8, "وضعیت همه طبقات و اتصال هر فایل به طبقه صحیح کنترل شد."],
  [9, "بارگذاری کامل فایل‌ها و پایان مأموریت برداشت ثبت شد."],
  [10, "پردازش، تشخیص مسیر، اتصال به Plan و آماده‌شدن بازدید کنترل شد."],
  [11, "اطلاع‌رسانی آماده‌شدن بازدید و تحویل پیام یا تماس جایگزین ثبت شد."],
  [12, "آموزش لازم برای مشاهده و استفاده مستقل انجام شد."],
  [13, "مشاهده مالک، پیگیری موفقیت مشتری و تعیین تکلیف موانع ثبت شد."],
]);

const control = (tag = "input") => {
  const node = document.createElement(tag);
  node.className = "stage-form__control";
  return node;
};

const field = (labelText, input) => {
  const label = element("label", "stage-form__field");
  label.append(element("span", "stage-form__label", labelText), input);
  return label;
};

const missionComplete = (mission) =>
  Boolean(
    mission.formF03.mission_completed &&
    mission.formF03.operations_confirmed &&
    mission.floorStates.length &&
    mission.floorStates.every(
      (floor) => floor.capture_state === "completed" &&
        floor.main_upload_started && floor.main_upload_completed &&
        floor.correct_floor_link && floor.operations_notified,
    ),
  );

const missionCreator = ({ experts, floors }) => {
  const form = element("section", "stage-form");
  const grid = element("div", "stage-form__grid");
  const expert = control("select");
  const start = control();
  const end = control();
  const location = control();
  const contactName = control();
  const contactMobile = control();
  const limitation = control("textarea");
  const floorSet = document.createElement("fieldset");
  const floorInputs = new Map();
  expert.add(new Option("انتخاب کارشناس برداشت", ""));
  experts.forEach((item) =>
    expert.add(new Option(`${item.display_name} — ${item.mobile}`, item.id)),
  );
  start.type = end.type = "datetime-local";
  contactMobile.type = "tel";
  limitation.rows = 2;
  floorSet.className = "checklist";
  floorSet.append(element("legend", "checklist__legend", "طبقات نوبت جدید"));
  floors.forEach((floor) => {
    const item = element("label", "checklist__item");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    item.append(checkbox, element("span", "", `${floor.code} — ${floor.name}`));
    floorSet.append(item);
    floorInputs.set(floor.id, { checkbox, item });
  });
  grid.append(
    field("کارشناس برداشت", expert), field("شروع برنامه‌ریزی‌شده", start),
    field("پایان برنامه‌ریزی‌شده", end), field("محل مأموریت", location),
    field("نام هماهنگ‌کننده محل", contactName),
    field("موبایل هماهنگ‌کننده", contactMobile),
    field("محدودیت یا توضیح (اختیاری)", limitation),
  );
  form.append(element("h2", "stage-form__legend", "ایجاد نوبت جدید برداشت"), grid, floorSet);
  const getData = () => ({
    expertUserId: expert.value,
    scheduledStart: start.value,
    scheduledEnd: end.value,
    location: location.value.trim(),
    siteContactName: contactName.value.trim(),
    siteContactMobile: contactMobile.value.trim(),
    limitation: limitation.value.trim(),
    floorIds: [...floorInputs]
      .filter(([, { checkbox }]) => checkbox.checked)
      .map(([id]) => id),
  });
  const validate = () => {
    const values = getData();
    const required = [expert, start, end, location, contactName, contactMobile];
    required.forEach((input) => input.setAttribute("aria-invalid", String(!input.value.trim())));
    const mobileInvalid = !/^09\d{9}$/.test(values.siteContactMobile);
    contactMobile.setAttribute("aria-invalid", String(mobileInvalid));
    const dateInvalid = !values.scheduledStart || !values.scheduledEnd ||
      new Date(values.scheduledEnd) <= new Date(values.scheduledStart);
    start.setAttribute("aria-invalid", String(dateInvalid));
    end.setAttribute("aria-invalid", String(dateInvalid));
    floorInputs.forEach(({ item }) =>
      item.classList.toggle("checklist__item--invalid", !values.floorIds.length),
    );
    return required.every((input) => input.value.trim()) && !mobileInvalid &&
      !dateInvalid && values.floorIds.length > 0;
  };
  return { element: form, getData, validate };
};

const executionPanel = ({ mission, floors, onSaved }) => {
  const panel = element("section", "floor-workspace");
  const start = control();
  const end = control();
  const confirmation = document.createElement("input");
  const confirmationItem = element("label", "checklist__item");
  const save = element("button", "button button--primary", "ثبت تکمیل چرخه عملیاتی این نوبت");
  start.type = end.type = "datetime-local";
  confirmation.type = "checkbox";
  save.type = "button";
  const floorNames = mission.floorStates.map(({ floor_id: id }) => {
    const floor = floors.find((item) => item.id === id);
    return floor ? `${floor.code} — ${floor.name}` : `Floor ${id}`;
  }).join("، ");
  confirmationItem.append(
    confirmation,
    element("span", "", "برداشت، ذخیره، بارگذاری، اتصال به طبقه صحیح و تأیید عملیات برای همه طبقات این نوبت انجام شده است."),
  );
  panel.append(
    element("h2", "stage-form__legend", `${mission.code} — اجرای چرخه`),
    element("p", "draft-info", `طبقات: ${floorNames}`),
    field("شروع واقعی برداشت", start), field("پایان واقعی برداشت", end),
    confirmationItem,
  );
  save.addEventListener("click", async () => {
    const invalid = !start.value || !end.value ||
      new Date(end.value) < new Date(start.value) || !confirmation.checked;
    start.setAttribute("aria-invalid", String(invalid));
    end.setAttribute("aria-invalid", String(invalid));
    confirmationItem.classList.toggle("checklist__item--invalid", invalid);
    if (invalid) return;
    save.disabled = true;
    try {
      for (const state of mission.floorStates) {
        await missionService.saveFloorCapture(mission.id, state.floor_id, {
          captureState: "completed", correctFloor: true,
          startPointConfirmed: true, mainCaptureStarted: true,
          continuousRoute: true, coverageCompleted: true,
          captureFinished: true, savedInMainApp: true,
          captureStartedAt: start.value, captureFinishedAt: end.value,
          mainUploadStarted: true, mainUploadCompleted: true,
          correctFloorLink: true, operationsNotified: true,
          failureReason: "",
        });
      }
      await missionService.saveF03(mission.id, {
        ...mission.formF03,
        assignment_accepted: true, site_entry_confirmed: true,
        permission_confirmed: true, ppe_ready: true, camera_ready: true,
        main_app_connected: true, battery_ready: true, storage_ready: true,
        project_floor_plan_confirmed: true, test_image_completed: true,
        mission_completed: true, operations_confirmed: true,
        started_at: new Date(start.value).toISOString(),
        finished_at: new Date(end.value).toISOString(),
      });
      await onSaved();
    } catch (error) {
      save.disabled = false;
      panel.append(element("p", "stage-actions__feedback", error.message));
    }
  });
  panel.append(save);
  return panel;
};

const reviewPanel = ({ mission, review, disabled, onSaved }) => {
  const panel = element("section", "stage-form");
  const checklist = document.createElement("fieldset");
  const items = new Map();
  const result = control("textarea");
  const save = element("button", "button button--primary", "ذخیره بازبینی این نوبت");
  checklist.className = "checklist";
  checklist.append(element("legend", "checklist__legend", "بازبینی چرخه مراحل ۵ تا ۱۳"));
  RECHECKS.forEach(([number, label]) => {
    const item = element("label", "checklist__item");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = Boolean(review?.[`stage_${number}_confirmed`]);
    checkbox.disabled = disabled;
    item.append(checkbox, element("span", "", label));
    checklist.append(item);
    items.set(number, { checkbox, item });
  });
  result.rows = 4;
  result.value = review?.independent_result ?? "";
  result.disabled = disabled;
  result.placeholder = "تعداد نوبت‌های مصوب و انجام‌شده، نتیجه مستقل هر چرخه یا علت توقف را ثبت کنید.";
  save.type = "button";
  save.hidden = disabled;
  panel.append(
    element("h2", "stage-form__legend", `${mission.code} — نتیجه نوبت`),
    checklist,
    field("نتیجه مستقل و مستند نوبت", result),
    save,
  );
  save.addEventListener("click", async () => {
    let valid = result.value.trim().length >= 2;
    items.forEach(({ checkbox, item }) => {
      item.classList.toggle("checklist__item--invalid", !checkbox.checked);
      valid = valid && checkbox.checked;
    });
    result.setAttribute("aria-invalid", String(result.value.trim().length < 2));
    if (!valid) return;
    save.disabled = true;
    try {
      await evaluationService.saveContinuationReview(mission.id, {
        ...Object.fromEntries([...items].map(([number, { checkbox }]) => [`stage${number}`, checkbox.checked])),
        independentResult: result.value.trim(),
      });
      await onSaved();
    } catch (error) {
      save.disabled = false;
      panel.append(element("p", "stage-actions__feedback", error.message));
    }
  });
  return panel;
};

export const StageFourteenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const user = sessionStore.getCurrentUser();
  const permissions = user?.permissions ?? [];
  const roleNames = (user?.roles ?? []).map(({ name }) => name);
  const canRead = permissions.includes("pilots.read");
  const canManage = permissions.includes("missions.manage");
  const canCoordinate = roleNames.some((name) => ["super_admin", "operations"].includes(name));
  const canSubmit = permissions.includes("checklists.manage");
  const canApprove = permissions.includes("gate_approval.approve");
  const canReject = permissions.includes("gate_approval.reject");

  const renderError = (message) => {
    const state = element("div", "error-state");
    const retry = element("button", "button button--primary", "تلاش مجدد");
    retry.type = "button";
    retry.addEventListener("click", () => load());
    state.append(element("p", "error-state__message", message), retry);
    page.replaceChildren(state);
  };

  const load = async (notice = "") => {
    if (!canRead) return renderError("برای مشاهده Stage 14 دسترسی لازم را ندارید.");
    page.replaceChildren(element("p", "loading-state", "در حال دریافت چرخه‌های ادامه برداشت..."));
    try {
      const [pilot, missions, floors, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId), missionService.getMissions(pilotId),
        dwgService.getFloors(pilotId), stageService.getSnapshots(pilotId, 14),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 14);
      if (!stage) return renderError("Stage 14 در ساختار این پرونده وجود ندارد.");
      if (stage.status === "locked" || pilot.currentStage < 14) {
        return renderError("Stage 14 تا زمان تأیید Stage 13 و عبور از G4 قفل است.");
      }
      const continuation = missions.filter(({ sequence }) => sequence >= 2);
      const reviews = new Map(await Promise.all(
        continuation.map(async (mission) => [
          mission.id,
          await evaluationService.getContinuationReview(mission.id),
        ]),
      ));
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 14 از ۱۹`),
        element("h1", "page-heading__title", "ادامه برداشت‌های پایلوت"),
        element("p", "draft-info", "برای هر نوبت جدید، مأموریت جدا صادر و چرخه مراحل ۵ تا ۱۳ تکرار و مستند می‌شود."),
        element("p", "draft-info", "شرط عبور: تعداد نوبت‌های مصوب انجام شده یا علت توقف آن‌ها مستند شده باشد."),
      );
      header.append(identity, element("span", "status-badge stage-workspace__status", STATUS_LABELS[stage.status] ?? stage.status));
      page.replaceChildren(back, header, feedback);

      if (["open", "needs_revision"].includes(stage.status) && canCoordinate) {
        const experts = await missionService.getCaptureExperts();
        const creator = missionCreator({ experts, floors });
        const create = element("button", "button button--ghost", "ایجاد نوبت جدید");
        create.type = "button";
        create.addEventListener("click", async () => {
          if (!creator.validate()) return;
          create.disabled = true;
          try {
            await missionService.createMission(pilot.id, creator.getData());
            await load("نوبت جدید برداشت ایجاد شد.");
          } catch (error) {
            feedback.textContent = error.message;
            create.disabled = false;
          }
        });
        page.append(creator.element, create);
      }

      continuation.forEach((mission) => {
        const complete = missionComplete(mission);
        const summary = element("p", "draft-info", `${mission.code} — ${formatPersianDate(mission.scheduledStart)} — ${complete ? "چرخه عملیاتی کامل" : "در انتظار تکمیل عملیات"}`);
        page.append(summary);
        if (!complete && canManage && ["open", "needs_revision"].includes(stage.status)) {
          page.append(executionPanel({ mission, floors, onSaved: () => load("چرخه عملیاتی نوبت ذخیره شد.") }));
        } else if (complete && ["open", "needs_revision"].includes(stage.status)) {
          page.append(reviewPanel({
            mission,
            review: reviews.get(mission.id),
            disabled: !canManage,
            onSaved: () => load("بازبینی نوبت ذخیره شد."),
          }));
        }
      });

      if (["open", "needs_revision"].includes(stage.status)) {
        const submit = element("button", "button button--primary", "ارسال Stage 14 برای بررسی");
        submit.type = "button";
        submit.hidden = !canSubmit;
        submit.disabled = !continuation.length;
        submit.addEventListener("click", async () => {
          submit.disabled = true;
          try {
            await stageService.submit(pilot.id, 14);
            await load("Stage 14 برای بررسی ارسال شد.");
          } catch (error) {
            feedback.textContent = error.message;
            submit.disabled = false;
          }
        });
        page.append(submit);
      }
      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(StageReviewPanel({
          pilotId: pilot.id, stageNumber: 14,
          title: "بررسی چرخه‌های ادامه برداشت",
          approveLabel: "تأیید و ورود به Stage 15",
          approvedNotice: "Stage 14 تأیید شد و Stage 15 باز شد.",
          rejectedNotice: "Stage 14 برای اصلاح برگشت داده شد.",
          canApprove, canReject, reload: load,
        }));
      }
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های تأییدشده Stage 14" }));
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 14 انجام نشد.");
    }
  };
  load();
  return page;
};

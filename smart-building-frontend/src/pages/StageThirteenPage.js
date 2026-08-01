import { sessionStore } from "../app/sessionStore.js";
import {
  StageReviewPanel,
  StageSnapshots,
  stageElement as element,
} from "../components/StageShared.js";
import { experienceService } from "../services/experienceService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { formatPersianDate } from "../utils/dateFormatter.js";

const STATUS_LABELS = Object.freeze({
  open: "باز",
  submitted: "در انتظار بررسی G4",
  approved: "تأییدشده",
  needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده",
});

const VIEWING_RESULTS = Object.freeze([
  "مشاهده موفق",
  "نیازمند آموزش",
  "مشکل فنی",
  "هنوز مشاهده نکرده",
  "عدم پاسخ",
]);

const ISSUE_ROUTES = Object.freeze({
  access: ["ورود یا دسترسی", "support", "پشتیبانی"],
  platform: ["اشکال سامانه", "technical", "تیم فنی"],
  coverage_quality: ["پوشش ناقص یا کیفیت برداشت", "operations", "عملیات"],
  training: ["نیاز آموزشی", "training", "واحد آموزش"],
  capability: ["قابلیت جدید", "product", "مدیر محصول"],
  continuation: ["تمایل به ادامه", "sales", "فروش"],
});

const toDateTimeLocal = (value) => {
  if (!value) return "";
  const explicit = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}Z`;
  const date = new Date(explicit);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
};

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

const followUpForm = ({ form, disabled, currentUserId }) => {
  const section = element("section", "stage-form");
  const firstGrid = element("div", "stage-form__grid");
  const secondGrid = element("div", "stage-form__grid");
  const issueGrid = element("div", "stage-form__grid");
  const ownerLoggedIn = document.createElement("input");
  const projectOpened = document.createElement("input");
  const mainTourViewed = document.createElement("input");
  const firstFollowUpAt = control();
  const viewingResult = control("select");
  const secondFollowUpAt = control();
  const useful = control("select");
  const coverageScore = control();
  const qualityScore = control();
  const satisfactionScore = control();
  const mostUsefulPart = control("textarea");
  const missingPart = control("textarea");
  const otherUsers = control("textarea");
  const moreTrainingNeeded = document.createElement("input");
  const issueDescription = control("textarea");
  const issueCategory = control("select");
  const issueRoute = control();
  const issueDueAt = control();

  firstFollowUpAt.type = secondFollowUpAt.type = issueDueAt.type = "datetime-local";
  coverageScore.type = qualityScore.type = satisfactionScore.type = "number";
  [coverageScore, qualityScore, satisfactionScore].forEach((input) => {
    input.min = "1";
    input.max = "10";
  });
  VIEWING_RESULTS.forEach((value) => viewingResult.add(new Option(value, value)));
  viewingResult.insertBefore(new Option("انتخاب وضعیت", ""), viewingResult.firstChild);
  useful.add(new Option("انتخاب نتیجه", ""));
  useful.add(new Option("بله، مفید بود", "true"));
  useful.add(new Option("خیر", "false"));
  issueCategory.add(new Option("بدون مشکل قابل ارجاع", ""));
  Object.entries(ISSUE_ROUTES).forEach(([value, [label]]) =>
    issueCategory.add(new Option(label, value)),
  );
  issueRoute.readOnly = true;
  issueDescription.rows = mostUsefulPart.rows = missingPart.rows = otherUsers.rows = 3;

  ownerLoggedIn.type = projectOpened.type = mainTourViewed.type =
    moreTrainingNeeded.type = "checkbox";
  ownerLoggedIn.checked = Boolean(form?.owner_logged_in);
  projectOpened.checked = Boolean(form?.project_opened);
  mainTourViewed.checked = Boolean(form?.main_tour_viewed);
  firstFollowUpAt.value = toDateTimeLocal(form?.first_follow_up_at);
  viewingResult.value = form?.viewing_result ?? "";
  secondFollowUpAt.value = toDateTimeLocal(form?.second_follow_up_at);
  useful.value = form?.useful == null ? "" : String(form.useful);
  coverageScore.value = form?.coverage_score ?? "";
  qualityScore.value = form?.quality_score ?? "";
  satisfactionScore.value = form?.satisfaction_score ?? "";
  mostUsefulPart.value = form?.most_useful_part ?? "";
  missingPart.value = form?.missing_part ?? "";
  otherUsers.value = form?.other_users ?? "";
  moreTrainingNeeded.checked = Boolean(form?.more_training_needed);
  issueDescription.value = form?.issue_description ?? "";
  issueCategory.value = form?.issue_category ?? "";
  issueDueAt.value = toDateTimeLocal(form?.issue_due_at);

  const syncRoute = () => {
    const route = ISSUE_ROUTES[issueCategory.value];
    issueRoute.value = route ? route[2] : "";
  };
  syncRoute();
  issueCategory.addEventListener("change", syncRoute);

  const firstChecks = document.createElement("fieldset");
  firstChecks.className = "checklist";
  firstChecks.append(element("legend", "checklist__legend", "پیگیری اول — حداکثر تا ۲۴ ساعت"));
  [
    [ownerLoggedIn, "مالک پیام را دریافت کرده و وارد حساب شده است."],
    [projectOpened, "پروژه و طبقه برای مالک باز شده است."],
    [mainTourViewed, "مالک بازدید اصلی را مشاهده کرده است."],
  ].forEach(([checkbox, label]) => {
    const item = element("label", "checklist__item");
    item.append(checkbox, element("span", "", label));
    firstChecks.append(item);
  });
  moreTrainingNeeded.disabled = disabled;
  const trainingItem = element("label", "checklist__item");
  trainingItem.append(
    moreTrainingNeeded,
    element("span", "", "مالک به آموزش بیشتری نیاز دارد."),
  );

  firstGrid.append(
    field("زمان پیگیری اول", firstFollowUpAt),
    field("نتیجه پیگیری اول", viewingResult),
  );
  secondGrid.append(
    field("زمان پیگیری دوم — روز ۳ تا ۵", secondFollowUpAt),
    field("آیا بازدید برای مالک مفید بود؟", useful),
    field("امتیاز پوشش مسیر از ۱۰", coverageScore),
    field("امتیاز کیفیت تصویر از ۱۰", qualityScore),
    field("امتیاز رضایت از ۱۰", satisfactionScore),
    field("مفیدترین بخش", mostUsefulPart),
    field("بخش ثبت‌نشده یا ناقص", missingPart),
    field("کاربران دیگری که به دسترسی نیاز دارند", otherUsers),
  );
  issueGrid.append(
    field("شرح مشکل یا بازخورد قابل ارجاع", issueDescription),
    field("نوع بازخورد", issueCategory),
    field("واحد ارجاع", issueRoute),
    field("موعد پاسخ یا اصلاح", issueDueAt),
  );
  section.append(
    element("h2", "stage-form__legend", "پیگیری اول"),
    firstChecks,
    firstGrid,
    element("h2", "stage-form__legend", "پیگیری دوم"),
    secondGrid,
    trainingItem,
    element("h2", "stage-form__legend", "ارجاع بازخورد"),
    issueGrid,
  );

  [
    ownerLoggedIn, projectOpened, mainTourViewed, firstFollowUpAt,
    viewingResult, secondFollowUpAt, useful, coverageScore, qualityScore,
    satisfactionScore, mostUsefulPart, missingPart, otherUsers,
    issueDescription, issueCategory, issueDueAt,
  ].forEach((input) => { input.disabled = disabled; });

  const getData = () => {
    const route = ISSUE_ROUTES[issueCategory.value];
    return {
      ownerLoggedIn: ownerLoggedIn.checked,
      projectOpened: projectOpened.checked,
      mainTourViewed: mainTourViewed.checked,
      firstFollowUpAt: firstFollowUpAt.value,
      viewingResult: viewingResult.value,
      secondFollowUpAt: secondFollowUpAt.value,
      useful: useful.value === "" ? null : useful.value === "true",
      coverageScore: Number(coverageScore.value) || null,
      qualityScore: Number(qualityScore.value) || null,
      satisfactionScore: Number(satisfactionScore.value) || null,
      mostUsefulPart: mostUsefulPart.value.trim(),
      missingPart: missingPart.value.trim(),
      otherUsers: otherUsers.value.trim(),
      moreTrainingNeeded: moreTrainingNeeded.checked,
      issueDescription: issueDescription.value.trim(),
      issueCategory: issueCategory.value,
      issueRoute: route?.[1] ?? "",
      issueOwnerUserId: issueDescription.value.trim() ? currentUserId : null,
      issueDueAt: issueDueAt.value,
      customerSuccessUserId: currentUserId,
    };
  };
  const validate = ({ forSubmit = false } = {}) => {
    const values = getData();
    const required = [
      [ownerLoggedIn, !values.ownerLoggedIn],
      [projectOpened, !values.projectOpened],
      [mainTourViewed, !values.mainTourViewed],
      [firstFollowUpAt, !values.firstFollowUpAt],
      [viewingResult, !values.viewingResult],
      [secondFollowUpAt, !values.secondFollowUpAt],
    ];
    const issueInvalid = Boolean(values.issueDescription) &&
      (!values.issueCategory || !values.issueDueAt);
    required.forEach(([input, invalid]) =>
      input.setAttribute("aria-invalid", String(forSubmit && invalid)),
    );
    issueCategory.setAttribute("aria-invalid", String(issueInvalid));
    issueDueAt.setAttribute("aria-invalid", String(issueInvalid));
    return (!forSubmit || required.every(([, invalid]) => !invalid)) &&
      !issueInvalid;
  };
  return { element: section, getData, validate };
};

const incidentCard = ({ incident, canManage, onClosed }) => {
  const card = element("article", "floor-workspace");
  const details = element("dl", "stage-project-summary");
  details.append(
    fieldValue("کد رخداد", incident.code),
    fieldValue("شدت", incident.severity),
    fieldValue("وضعیت", incident.status),
    fieldValue("شرح", incident.description),
    fieldValue("مهلت پاسخ", formatPersianDate(incident.response_due_at)),
  );
  card.append(element("h2", "stage-form__legend", "رخداد بحرانی باز"), details);
  if (canManage) {
    const form = element("div", "stage-form__grid");
    const rootCause = control("textarea");
    const correctiveAction = control("textarea");
    const result = control("textarea");
    const evidence = control("textarea");
    const lessonsLearned = control("textarea");
    const close = element("button", "button button--ghost", "بستن رخداد پس از تأیید اصلاح");
    [rootCause, correctiveAction, result, evidence, lessonsLearned].forEach((input) => {
      input.rows = 2;
    });
    close.type = "button";
    form.append(
      field("علت ریشه‌ای", rootCause),
      field("اقدام اصلاحی", correctiveAction),
      field("نتیجه", result),
      field("شاهد یا مدرک (اختیاری)", evidence),
      field("درس‌آموخته", lessonsLearned),
    );
    close.addEventListener("click", async () => {
      const required = [rootCause, correctiveAction, result, lessonsLearned];
      required.forEach((input) =>
        input.setAttribute("aria-invalid", String(!input.value.trim())),
      );
      if (required.some((input) => !input.value.trim())) return;
      close.disabled = true;
      try {
        await experienceService.closeIncident(incident.id, {
          rootCause: rootCause.value.trim(),
          correctiveAction: correctiveAction.value.trim(),
          result: result.value.trim(),
          evidence: evidence.value.trim(),
          lessonsLearned: lessonsLearned.value.trim(),
        });
        await onClosed();
      } catch (error) {
        close.disabled = false;
        card.append(element("p", "stage-actions__feedback", error.message));
      }
    });
    card.append(form, close);
  }
  return card;
};

const fieldValue = (label, value) => {
  const row = document.createElement("div");
  row.append(element("dt", "", label), element("dd", "", value || "—"));
  return row;
};

export const StageThirteenPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const currentUser = sessionStore.getCurrentUser();
  const permissions = currentUser?.permissions ?? [];
  const canRead = permissions.includes("pilots.read");
  const canEdit = permissions.includes("customer_success.manage");
  const canManageIncidents = permissions.includes("incidents.manage");
  const canSubmit = permissions.includes("checklists.manage");
  const canApprove = permissions.includes("gate_approval.approve");
  const canReject = permissions.includes("gate_approval.reject");

  const renderError = (message) => {
    const state = element("div", "error-state");
    const retry = element("button", "button button--primary", "تلاش مجدد");
    const back = element("a", "button button--ghost", "بازگشت به جزئیات");
    retry.type = "button";
    retry.addEventListener("click", () => load());
    back.href = `#/pilots/${pilotId}`;
    state.append(element("p", "error-state__message", message), retry, back);
    page.replaceChildren(state);
  };

  const load = async (notice = "") => {
    if (!canRead) {
      renderError("برای مشاهده Stage 13 دسترسی لازم را ندارید.");
      return;
    }
    page.replaceChildren(element("p", "loading-state", "در حال دریافت پیگیری‌های مشتری..."));
    try {
      const [pilot, formF04, incidents, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        experienceService.getF04(pilotId),
        experienceService.getIncidents(pilotId),
        stageService.getSnapshots(pilotId, 13),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 13);
      if (!stage) return renderError("Stage 13 در ساختار این پرونده وجود ندارد.");
      if (stage.status === "locked" || pilot.currentStage < 13) {
        return renderError("Stage 13 تا زمان تأیید Stage 12 قفل است.");
      }
      const openCritical = incidents.filter(
        ({ severity, status }) => severity === "critical" && status !== "closed",
      );
      const editable = canEdit && ["open", "needs_revision"].includes(stage.status);
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const form = followUpForm({
        form: formF04,
        disabled: !editable,
        currentUserId: currentUser.id,
      });
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 13 از ۱۹`),
        element("h1", "page-heading__title", "پیگیری موفقیت مشتری"),
        element("p", "draft-info", "کنترل استفاده واقعی، تجربه ارزش و رفع مانع؛ پیگیری اول تا ۲۴ ساعت و پیگیری دوم در روزهای ۳ تا ۵."),
        element("p", "draft-info", "شرط عبور: مالک بازدید را مشاهده کرده و تمام مشکلات بحرانی بسته شده باشند."),
      );
      header.append(
        identity,
        element("span", "status-badge stage-workspace__status", `${STATUS_LABELS[stage.status] ?? stage.status} — G4`),
      );
      page.replaceChildren(back, header, feedback, form.element);
      openCritical.forEach((incident) =>
        page.append(incidentCard({
          incident,
          canManage: canManageIncidents,
          onClosed: () => load("رخداد بحرانی بسته شد و وضعیت G4 به‌روزرسانی شد."),
        })),
      );

      if (["open", "needs_revision"].includes(stage.status)) {
        const actions = element("div", "stage-actions");
        const save = element("button", "button button--ghost", "ذخیره پیگیری‌ها");
        const submit = element("button", "button button--primary", "ارسال Stage 13 برای بررسی G4");
        save.type = submit.type = "button";
        save.hidden = !canEdit;
        submit.hidden = !canSubmit;
        submit.disabled = openCritical.length > 0;
        save.addEventListener("click", async () => {
          if (!form.validate()) return;
          save.disabled = true;
          try {
            await experienceService.saveF04FollowUp(pilot.id, form.getData());
            await load("اطلاعات پیگیری مشتری ذخیره شد.");
          } catch (error) {
            feedback.textContent = error.message;
            save.disabled = false;
          }
        });
        submit.addEventListener("click", async () => {
          if (!form.validate({ forSubmit: true })) return;
          submit.disabled = true;
          try {
            if (canEdit) await experienceService.saveF04FollowUp(pilot.id, form.getData());
            await stageService.submit(pilot.id, 13);
            await load("Stage 13 برای بررسی G4 ارسال شد.");
          } catch (error) {
            feedback.textContent = error.message;
            submit.disabled = false;
          }
        });
        actions.append(save, submit);
        if (openCritical.length) {
          actions.append(element("p", "stage-actions__feedback", "تا بسته‌شدن همه رخدادهای بحرانی، عبور از G4 ممکن نیست."));
        }
        page.append(actions);
      }

      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(StageReviewPanel({
          pilotId: pilot.id,
          stageNumber: 13,
          title: "بررسی نهایی پیگیری موفقیت مشتری — G4",
          approveLabel: "تأیید G4 و ورود به Stage 14",
          approvedNotice: "G4 تأیید شد و Stage 14 باز شد.",
          rejectedNotice: "Stage 13 برای اصلاح برگشت داده شد.",
          canApprove,
          canReject,
          reload: load,
          onApproved: async () => {
            const refreshedPilot = await pilotService.getPilotById(pilot.id);
            if (refreshedPilot.currentStage === 14) {
              window.location.hash = `#/pilots/${pilot.id}/stages/14`;
              return;
            }
            await load(
              "Stage 13 تأیید شد، اما Stage 14 هنوز از سمت سرور فعال نشده است.",
            );
          },
        }));
      }
      page.append(StageSnapshots({ snapshots, title: "نسخه‌های تأییدشده G4" }));
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 13 انجام نشد.");
    }
  };
  load();
  return page;
};

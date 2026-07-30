import { sessionStore } from "../app/sessionStore.js";
import { clearNavigationGuard, setNavigationGuard } from "../app/navigationGuard.js";
import {
  StageReviewPanel,
  StageSnapshots,
  stageElement as element,
} from "../components/StageShared.js";
import { dwgService } from "../services/dwgService.js";
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

const field = ({ id, label, type = "text", value = "", disabled = false }) => {
  const wrapper = element("div", "stage-form__field");
  const labelNode = element("label", "stage-form__label", label);
  const control = document.createElement("input");
  labelNode.htmlFor = id;
  control.id = id;
  control.type = type;
  control.value = value;
  control.disabled = disabled;
  control.className = "stage-form__control";
  wrapper.append(labelNode, control);
  return { wrapper, control };
};

const missionForm = ({ experts, floors, onChange }) => {
  const form = document.createElement("form");
  const information = document.createElement("fieldset");
  const grid = element("div", "stage-form__grid");
  const expertField = element("div", "stage-form__field");
  const expertLabel = element("label", "stage-form__label", "کارشناس برداشت");
  const expert = document.createElement("select");
  const start = field({
    id: "stage5-start",
    label: "شروع مأموریت",
    type: "datetime-local",
  });
  const end = field({
    id: "stage5-end",
    label: "پایان مأموریت",
    type: "datetime-local",
  });
  const location = field({
    id: "stage5-location",
    label: "نشانی یا محل دقیق مأموریت",
  });
  const contactName = field({
    id: "stage5-contact-name",
    label: "نام هماهنگ‌کننده محل",
  });
  const contactMobile = field({
    id: "stage5-contact-mobile",
    label: "موبایل هماهنگ‌کننده محل",
    type: "tel",
  });
  const limitationField = element("div", "stage-form__field");
  const limitationLabel = element(
    "label",
    "stage-form__label",
    "محدودیت یا توضیح تکمیلی (اختیاری)",
  );
  const limitation = document.createElement("textarea");
  const floorSection = document.createElement("fieldset");
  const floorItems = new Map();

  form.className = "stage-form";
  information.className = "stage-form__section";
  information.append(
    element("legend", "stage-form__legend", "برنامه‌ریزی مأموریت"),
  );
  expertLabel.htmlFor = "stage5-expert";
  expert.id = "stage5-expert";
  expert.className = "stage-form__control";
  expert.append(new Option("انتخاب کارشناس", ""));
  experts.forEach((item) =>
    expert.append(new Option(`${item.display_name} — ${item.mobile}`, item.id)),
  );
  expertField.append(expertLabel, expert);
  limitationLabel.htmlFor = "stage5-limitation";
  limitation.id = "stage5-limitation";
  limitation.className = "stage-form__control";
  limitationField.append(limitationLabel, limitation);
  grid.append(
    expertField,
    start.wrapper,
    end.wrapper,
    location.wrapper,
    contactName.wrapper,
    contactMobile.wrapper,
    limitationField,
  );
  information.append(grid);

  floorSection.className = "checklist";
  floorSection.append(
    element("legend", "checklist__legend", "طبقات این مأموریت"),
  );
  floors.forEach((floor) => {
    const item = element("label", "checklist__item");
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = true;
    checkbox.addEventListener("change", () => {
      item.classList.remove("checklist__item--invalid");
      onChange();
    });
    item.append(
      checkbox,
      element("span", "", `${floor.code} — ${floor.name}`),
    );
    floorSection.append(item);
    floorItems.set(floor.id, { checkbox, item });
  });
  [expert, start.control, end.control, location.control, contactName.control,
    contactMobile.control, limitation].forEach((control) => {
    control.addEventListener("input", () => {
      control.removeAttribute("aria-invalid");
      onChange();
    });
  });
  form.append(information, floorSection);

  const required = [
    expert,
    start.control,
    end.control,
    location.control,
    contactName.control,
    contactMobile.control,
  ];
  return {
    element: form,
    validate: () => {
      let valid = true;
      required.forEach((control) => {
        const invalid = !control.value.trim();
        control.setAttribute("aria-invalid", String(invalid));
        valid = valid && !invalid;
      });
      const mobileInvalid = !/^09\d{9}$/.test(
        contactMobile.control.value.trim(),
      );
      contactMobile.control.setAttribute(
        "aria-invalid",
        String(mobileInvalid),
      );
      valid = valid && !mobileInvalid;
      const dateInvalid =
        !start.control.value ||
        !end.control.value ||
        new Date(end.control.value) <= new Date(start.control.value);
      start.control.setAttribute("aria-invalid", String(dateInvalid));
      end.control.setAttribute("aria-invalid", String(dateInvalid));
      valid = valid && !dateInvalid;
      const selected = [...floorItems.values()].filter(
        ({ checkbox }) => checkbox.checked,
      );
      floorItems.forEach(({ item }) =>
        item.classList.toggle("checklist__item--invalid", !selected.length),
      );
      return valid && selected.length > 0;
    },
    getData: () => ({
      expertUserId: expert.value,
      scheduledStart: start.control.value,
      scheduledEnd: end.control.value,
      floorIds: [...floorItems]
        .filter(([, value]) => value.checkbox.checked)
        .map(([id]) => id),
      location: location.control.value.trim(),
      siteContactName: contactName.control.value.trim(),
      siteContactMobile: contactMobile.control.value.trim(),
      limitation: limitation.value.trim(),
    }),
  };
};

const missionSummary = (mission, floors, expertName) => {
  const section = element("section", "stage-form__section mission-summary");
  const list = element("dl", "stage-project-summary");
  const floorNames = mission.floorStates
    .map(({ floor_id: floorId }) => floors.find(({ id }) => id === floorId))
    .filter(Boolean)
    .map(({ code, name }) => `${code} — ${name}`)
    .join("، ");
  const rows = [
    ["کد مأموریت", mission.code],
    ["کارشناس برداشت", expertName || `کاربر ${mission.expertUserId}`],
    ["شروع", formatPersianDate(mission.scheduledStart)],
    ["پایان", formatPersianDate(mission.scheduledEnd)],
    ["محل", mission.location],
    ["هماهنگ‌کننده", `${mission.siteContactName} — ${mission.siteContactMobile}`],
    ["طبقات", floorNames],
    ["محدودیت", mission.limitation || "ندارد"],
  ];
  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.append(element("dt", "", label), element("dd", "", value));
    list.append(row);
  });
  const notification = mission.notifications.at(-1);
  section.append(
    element("h2", "stage-form__legend", "مأموریت ثبت‌شده"),
    list,
    element(
      "p",
      `mission-notice mission-notice--${notification?.status ?? "unknown"}`,
      notification?.status === "delivered"
        ? "اعلان مأموریت با موفقیت برای کارشناس ارسال شده است."
        : `ارسال اعلان کامل نشده است: ${notification?.lastError ?? "وضعیت نامشخص"}`,
    ),
  );
  return section;
};

export const StageFivePage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const user = sessionStore.getCurrentUser();
  const permissions = user?.permissions ?? [];
  const roleNames = (user?.roles ?? []).map(({ name }) => name);
  const canCoordinate = roleNames.some((name) =>
    ["super_admin", "operations"].includes(name),
  );
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
    clearNavigationGuard();
    page.replaceChildren(
      element("p", "loading-state", "در حال دریافت اطلاعات Stage 5..."),
    );
    try {
      const [pilot, missions, floors, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        missionService.getMissions(pilotId),
        dwgService.getFloors(pilotId),
        stageService.getSnapshots(pilotId, 5),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 5);
      if (stage.status === "locked") {
        renderError("Stage 5 تا زمان تأیید Stage 4 و عبور از G2 قفل است.");
        return;
      }
      const mission = missions.at(-1);
      const experts = canCoordinate
        ? await missionService.getCaptureExperts()
        : [];
      const expertName = experts.find(
        ({ id }) => id === mission?.expertUserId,
      )?.display_name;
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const feedback = element("p", "stage-actions__feedback", notice);
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 5 از ۱۹`),
        element("h1", "page-heading__title", "برنامه‌ریزی و تخصیص مأموریت"),
        element(
          "p",
          "draft-info",
          "هماهنگ‌کننده مأموریت را می‌سازد؛ سپس کارشناس منتخب باید تخصیص را با حساب خودش بپذیرد.",
        ),
      );
      header.append(
        identity,
        element(
          "span",
          "status-badge stage-workspace__status",
          STATUS_LABELS[stage.status] ?? stage.status,
        ),
      );
      page.replaceChildren(back, header, feedback);

      if (!mission) {
        if (!canCoordinate) {
          page.append(
            element(
              "p",
              "draft-info",
              "هنوز مأموریتی ثبت نشده است. هماهنگ‌کننده عملیات باید ابتدا مأموریت را ایجاد کند.",
            ),
          );
        } else if (!experts.length) {
          page.append(
            element(
              "p",
              "error-state__message",
              "کارشناس برداشت فعال وجود ندارد. ابتدا در مدیریت کاربران، نقش «کارشناس برداشت» را به یک کاربر فعال بدهید.",
            ),
          );
        } else {
          const form = missionForm({
            experts,
            floors,
            onChange: () =>
              setNavigationGuard(() =>
                window.confirm(
                  "اطلاعات مأموریت ذخیره نشده‌اند. از صفحه خارج می‌شوید؟",
                ),
              ),
          });
          const actions = element("div", "stage-actions");
          const create = element(
            "button",
            "button button--primary",
            "ایجاد و ارسال مأموریت",
          );
          create.type = "button";
          create.addEventListener("click", async () => {
            if (!form.validate()) {
              feedback.textContent = "فیلدهای قرمزشده را تکمیل یا اصلاح کنید.";
              return;
            }
            create.disabled = true;
            try {
              await missionService.createMission(pilot.id, form.getData());
              clearNavigationGuard();
              await load(
                "مأموریت ایجاد و اعلان آن برای کارشناس برداشت ثبت شد.",
              );
            } catch (error) {
              feedback.textContent = error.message;
              create.disabled = false;
            }
          });
          actions.append(create);
          page.append(form.element, actions);
        }
      } else {
        page.append(missionSummary(mission, floors, expertName));
        const isAssignedExpert = user?.id === mission.expertUserId;
        if (!mission.formF03.assignment_accepted) {
          if (isAssignedExpert) {
            const acceptance = element("section", "checklist");
            const label = element("label", "checklist__item");
            const checkbox = document.createElement("input");
            const accept = element(
              "button",
              "button button--primary",
              "ثبت پذیرش مأموریت",
            );
            checkbox.type = "checkbox";
            accept.type = "button";
            accept.disabled = true;
            checkbox.addEventListener("change", () => {
              accept.disabled = !checkbox.checked;
            });
            label.append(
              checkbox,
              element(
                "span",
                "",
                "زمان، محل و طبقات مأموریت را بررسی کردم و این مأموریت را می‌پذیرم.",
              ),
            );
            accept.addEventListener("click", async () => {
              accept.disabled = true;
              try {
                await missionService.acceptAssignment(mission);
                await load("پذیرش مأموریت ثبت شد؛ Stage 5 آماده ارسال است.");
              } catch (error) {
                feedback.textContent = error.message;
                accept.disabled = false;
              }
            });
            acceptance.append(
              element("h2", "checklist__legend", "تأیید کارشناس"),
              label,
              accept,
            );
            page.append(acceptance);
          } else {
            page.append(
              element(
                "p",
                "draft-info",
                "در انتظار ورود کارشناس منتخب و پذیرش مأموریت هستیم.",
              ),
            );
          }
        } else if (["open", "needs_revision"].includes(stage.status)) {
          const actions = element("div", "stage-actions");
          const submit = element(
            "button",
            "button button--primary",
            "ارسال Stage 5 برای بررسی",
          );
          submit.type = "button";
          submit.hidden = !canSubmit;
          submit.addEventListener("click", async () => {
            submit.disabled = true;
            try {
              await stageService.submit(pilot.id, 5);
              await load("Stage 5 برای بررسی ارسال شد.");
            } catch (error) {
              feedback.textContent = error.message;
              submit.disabled = false;
            }
          });
          actions.append(submit);
          page.append(actions);
        }
      }
      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(
          StageReviewPanel({
            pilotId: pilot.id,
            stageNumber: 5,
            title: "بررسی تخصیص مأموریت",
            approveLabel: "تأیید و ورود به Stage 6",
            approvedNotice: "Stage 5 تأیید شد و Stage 6 باز شد.",
            rejectedNotice: "Stage 5 برای اصلاح برگشت داده شد.",
            canApprove,
            canReject,
            reload: load,
          }),
        );
      }
      page.append(
        StageSnapshots({
          snapshots,
          title: "نسخه‌های تأییدشده Stage 5",
        }),
      );
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 5 انجام نشد.");
    }
  };
  load();
  return page;
};

import { sessionStore } from "../app/sessionStore.js";
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

const CAPTURE_STATE_LABELS = Object.freeze({
  not_started: "شروع نشده",
  incomplete: "ناقص",
  not_done: "انجام نشده",
  needs_revision: "نیازمند اصلاح",
  completed: "تکمیل‌شده",
});

const floorResult = ({ floor, state, pilotId }) => {
  const card = element("article", "floor-workspace");
  const header = element("div", "floor-workspace__header");
  const details = element("dl", "stage-project-summary");
  const status = CAPTURE_STATE_LABELS[state.capture_state] ??
    state.capture_state;
  const rows = [
    ["وضعیت برداشت", status],
    ["شروع برداشت", formatPersianDate(state.capture_started_at)],
    ["پایان برداشت", formatPersianDate(state.capture_finished_at)],
    ["دلیل نقص یا اصلاح", state.failure_reason || "ندارد"],
  ];
  rows.forEach(([label, value]) => {
    const row = document.createElement("div");
    row.append(element("dt", "", label), element("dd", "", value));
    details.append(row);
  });
  header.append(
    element("h2", "stage-form__legend", `${floor.code} — ${floor.name}`),
    element(
      "span",
      `stage-status stage-status--${
        state.capture_state === "completed" ? "approved" : "needs_revision"
      }`,
      status,
    ),
  );
  card.append(header, details);
  if (state.capture_state === "not_started") {
    const edit = element(
      "a",
      "button button--ghost",
      "تکمیل اطلاعات در Stage 7",
    );
    edit.href = `#/pilots/${pilotId}/stages/7`;
    card.append(edit);
  }
  return card;
};

export const StageEightPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
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
    page.replaceChildren(
      element("p", "loading-state", "در حال کنترل نتایج چندطبقه..."),
    );
    try {
      const [pilot, missions, floors, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        missionService.getMissions(pilotId),
        dwgService.getFloors(pilotId),
        stageService.getSnapshots(pilotId, 8),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 8);
      if (stage.status === "locked") {
        renderError("Stage 8 تا زمان تأیید Stage 7 قفل است.");
        return;
      }
      const mission = missions.at(-1);
      if (!mission) {
        renderError("مأموریت فعال برای کنترل طبقات پیدا نشد.");
        return;
      }
      const unresolved = mission.floorStates.filter(
        ({ capture_state: captureState }) => captureState === "not_started",
      );
      const performedFloors = mission.floorStates.filter(
        ({ capture_state: captureState }) => captureState !== "not_started",
      );
      const resolutionChecks = [
        {
          label:
            "تعداد فایل‌های ذخیره‌شده با تعداد طبقات انجام‌شده برابر است.",
          checked: performedFloors.every(
            ({ saved_in_main_app: saved }) => saved,
          ),
        },
        {
          label: "هیچ فایل بدون نام یا طبقه مشخص باقی نمانده است.",
          checked: mission.floorStates.every(({ floor_id: floorId }) =>
            floors.some(({ id }) => id === floorId),
          ),
        },
        {
          label: "طبقات انجام‌نشده و علت آن‌ها ثبت شده‌اند.",
          checked: mission.floorStates.every(
            ({ capture_state: captureState, failure_reason: reason }) =>
              captureState === "completed" ||
              (captureState !== "not_started" && Boolean(reason)),
          ),
        },
      ];
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element(
          "span",
          "page-heading__eyebrow",
          `${pilot.code} — ${mission.code} — Stage 8 از ۱۹`,
        ),
        element("h1", "page-heading__title", "کنترل نتیجه چندطبقه"),
        element(
          "p",
          "draft-info",
          unresolved.length
            ? `${unresolved.length} طبقه هنوز تعیین تکلیف نشده است.`
            : "تمام طبقات مأموریت تعیین تکلیف شده‌اند.",
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
      const cards = mission.floorStates.map((state) => {
        const floor = floors.find(({ id }) => id === state.floor_id);
        return floor ? floorResult({ floor, state, pilotId: pilot.id }) : null;
      }).filter(Boolean);
      const checklist = document.createElement("fieldset");
      checklist.className = "checklist";
      checklist.append(
        element("legend", "checklist__legend", "کنترل برداشت چندطبقه"),
      );
      resolutionChecks.forEach(({ label, checked }) => {
        const item = element(
          "label",
          `checklist__item${checked ? "" : " checklist__item--invalid"}`,
        );
        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = checked;
        checkbox.disabled = true;
        item.append(checkbox, element("span", "", label));
        checklist.append(item);
      });
      const allResolutionChecksPassed = resolutionChecks.every(
        ({ checked }) => checked,
      );
      page.replaceChildren(back, header, feedback, checklist, ...cards);

      if (["open", "needs_revision"].includes(stage.status)) {
        const actions = element("div", "stage-actions");
        const submit = element(
          "button",
          "button button--primary",
          "ارسال Stage 8 برای بررسی",
        );
        submit.type = "button";
        submit.hidden = !canSubmit;
        submit.disabled =
          unresolved.length > 0 || !allResolutionChecksPassed;
        submit.addEventListener("click", async () => {
          submit.disabled = true;
          try {
            await stageService.submit(pilot.id, 8);
            await load("Stage 8 برای بررسی ارسال شد.");
          } catch (error) {
            feedback.textContent = error.message;
            submit.disabled = false;
          }
        });
        actions.append(submit);
        if (unresolved.length) {
          actions.append(
            element(
              "p",
              "stage-actions__feedback",
              "ابتدا طبقات شروع‌نشده را در Stage 7 تعیین تکلیف کنید.",
            ),
          );
        }
        page.append(actions);
      }

      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(
          StageReviewPanel({
            pilotId: pilot.id,
            stageNumber: 8,
            title: "بررسی نتیجه چندطبقه",
            approveLabel: "تأیید و ورود به Stage 9",
            approvedNotice: "Stage 8 تأیید شد و Stage 9 باز شد.",
            rejectedNotice: "Stage 8 برای اصلاح برگشت داده شد.",
            canApprove,
            canReject,
            reload: load,
          }),
        );
      }
      page.append(
        StageSnapshots({
          snapshots,
          title: "نسخه‌های تأییدشده Stage 8",
        }),
      );
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 8 انجام نشد.");
    }
  };
  load();
  return page;
};

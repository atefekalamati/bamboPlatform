import { sessionStore } from "../app/sessionStore.js";
import {
  clearNavigationGuard,
  createUnsavedChangesGuard,
  setNavigationGuard,
} from "../app/navigationGuard.js";
import { StageTwoForm } from "../components/StageTwoForm.js";
import { getStageReviewAccess } from "../features/stages/stageReviewAccess.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { formatPersianDateTime } from "../utils/dateFormatter.js";
import { translateDisplayValue } from "../utils/displayText.js";

const LABELS = {
  open: "باز",
  submitted: "در انتظار بررسی",
  approved: "تأییدشده",
  needs_revision: "نیازمند اصلاح",
  locked: "قفل‌شده",
};
const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

const snapshotsView = (snapshots) => {
  const section = element("section", "stage-snapshots");
  section.append(element("h2", "stage-form__legend", "نسخه‌های تأییدشده G1"));
  if (!snapshots.length) {
    section.append(element("p", "draft-info", "هنوز Snapshot تأییدشده‌ای وجود ندارد."));
    return section;
  }
  const list = element("ul", "stage-snapshots__list");
  snapshots.forEach((snapshot) => {
    const item = element("li", "stage-snapshots__item");
    item.append(
      element("strong", "", `نسخه ${snapshot.version}`),
      element("span", "", snapshot.name),
      element("span", "", formatPersianDateTime(snapshot.created_at)),
      element("code", "", snapshot.content_hash),
    );
    list.append(item);
  });
  section.append(list);
  return section;
};

const reviewPanel = ({ pilotId, canApprove, canReject, reload }) => {
  const panel = element("section", "stage-review");
  const comment = document.createElement("textarea");
  const corrections = document.createElement("textarea");
  const feedback = element("p", "stage-actions__feedback");
  const actions = element("div", "form-actions");
  const approve = element("button", "button button--primary", "تأیید و عبور از G1");
  const reject = element("button", "button button--ghost", "رد و درخواست اصلاح");
  panel.append(element("h2", "stage-form__legend", "بررسی Gate پذیرش"));
  comment.className = "stage-form__control";
  comment.placeholder = "توضیح بازبین (اختیاری)";
  corrections.className = "stage-form__control";
  corrections.placeholder = "موارد اصلاح؛ هر مورد در یک خط";
  approve.type = "button";
  reject.type = "button";
  approve.hidden = !canApprove;
  reject.hidden = !canReject;
  approve.addEventListener("click", async () => {
    approve.disabled = true;
    try {
      await stageService.approve(pilotId, 2, comment.value.trim());
      await reload("Stage 2 و G1 تأیید شدند؛ Stage 3 باز شد.");
    } catch (error) {
      feedback.textContent = error.message;
      approve.disabled = false;
    }
  });
  reject.addEventListener("click", async () => {
    const correctionItems = corrections.value
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean);
    const reason = comment.value.trim();
    if (!reason && !correctionItems.length) {
      corrections.setAttribute("aria-invalid", "true");
      feedback.textContent = "دلیل رد یا حداقل یک مورد اصلاح را وارد کنید.";
      return;
    }
    reject.disabled = true;
    try {
      await stageService.reject(pilotId, 2, { reason, correctionItems });
      await reload("Stage 2 برای اصلاح برگشت داده شد و G1 عبور نکرد.");
    } catch (error) {
      feedback.textContent = error.message;
      reject.disabled = false;
    }
  });
  actions.append(approve, reject);
  panel.append(comment, corrections, actions, feedback);
  return panel;
};

export const StageTwoPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canEdit = permissions.includes("forms.manage");
  const canSubmit = permissions.includes("checklists.manage");
  const { canApprove, canReject } = getStageReviewAccess(
    sessionStore.getCurrentUser(),
    2,
  );

  const renderError = (message, retry) => {
    const state = element("div", "error-state");
    const back = element("a", "button button--ghost", "بازگشت به جزئیات");
    const retryButton = element("button", "button button--primary", "تلاش مجدد");
    back.href = `#/pilots/${pilotId}`;
    retryButton.type = "button";
    retryButton.addEventListener("click", retry);
    state.append(element("p", "error-state__message", message), retryButton, back);
    page.replaceChildren(state);
  };

  const load = async (notice = "") => {
    clearNavigationGuard();
    page.replaceChildren(element("p", "loading-state", "در حال دریافت Stage 2..."));
    try {
      const [pilot, f01, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        stageService.getF01(pilotId),
        stageService.getSnapshots(pilotId, 2),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 2);
      if (stage.status === "locked") {
        renderError("Stage 2 تا زمان تأیید Stage 1 قفل است.", load);
        return;
      }
      if (!f01) {
        renderError("فرم F01 مرحله ۱ هنوز ثبت نشده است.", load);
        return;
      }
      const gate = pilot.gates.find(({ code }) => code === "G1");
      const editable = ["open", "needs_revision"].includes(stage.status) && canEdit;
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const status = element(
        "span",
        "status-badge stage-workspace__status",
        `${LABELS[stage.status] ?? translateDisplayValue(stage.status, "وضعیت نامشخص")} — گیت ۱: ${translateDisplayValue(gate?.status ?? "locked", "وضعیت نامشخص")}`,
      );
      const feedback = element("p", "stage-actions__feedback", notice);
      const form = StageTwoForm({
        initialData: f01,
        disabled: !editable,
        onChange: () => {
          status.textContent = "تغییرات ذخیره‌نشده";
          setNavigationGuard(
            createUnsavedChangesGuard(
              "تغییرات ذخیره نشده‌اند. از صفحه خارج می‌شوید؟",
            ),
          );
        },
      });
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 2 از ۱۹`),
        element("h1", "page-heading__title", "معرفی و موافقت"),
      );
      header.append(identity, status);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      back.href = `#/pilots/${pilot.id}`;
      page.replaceChildren(back, header, feedback, form.element);
      if (editable) {
        const actions = element("div", "stage-actions");
        const save = element("button", "button button--ghost", "ذخیره بخش دوم F01");
        const submit = element("button", "button button--primary", "ارسال برای بررسی G1");
        save.type = "button";
        submit.type = "button";
        submit.hidden = !canSubmit;
        const saveForm = async () => {
          save.disabled = true;
          await stageService.saveF01(pilot.id, form.getData());
          clearNavigationGuard();
          feedback.textContent = "اطلاعات Stage 2 در F01 ذخیره شد.";
          status.textContent = `${LABELS[stage.status] ?? translateDisplayValue(stage.status, "وضعیت نامشخص")} — گیت ۱: ${translateDisplayValue(gate?.status, "وضعیت نامشخص")}`;
          save.disabled = false;
        };
        save.addEventListener("click", async () => {
          try {
            await saveForm();
          } catch (error) {
            feedback.textContent = error.message;
            save.disabled = false;
          }
        });
        submit.addEventListener("click", async () => {
          if (form.validate().length) {
            feedback.textContent = "فیلدها و موارد قرمزشده باید اصلاح شوند.";
            return;
          }
          submit.disabled = true;
          try {
            await saveForm();
            await stageService.submit(pilot.id, 2);
            await load("Stage 2 برای بررسی G1 ارسال شد.");
          } catch (error) {
            feedback.textContent = error.message;
            submit.disabled = false;
          }
        });
        actions.append(save, submit);
        page.append(actions);
      }
      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(
          reviewPanel({
            pilotId: pilot.id,
            canApprove,
            canReject,
            reload: load,
          }),
        );
      }
      page.append(snapshotsView(snapshots));
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 2 انجام نشد.", load);
    }
  };
  load();
  return page;
};

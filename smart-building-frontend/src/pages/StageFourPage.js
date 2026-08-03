import { sessionStore } from "../app/sessionStore.js";
import {
  clearNavigationGuard,
  createUnsavedChangesGuard,
  setNavigationGuard,
} from "../app/navigationGuard.js";
import { StageFourForm } from "../components/StageFourForm.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { formatPersianDate } from "../utils/dateFormatter.js";
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
  section.append(
    element("h2", "stage-form__legend", "نسخه‌های تأییدشده G2"),
  );
  if (!snapshots.length) {
    section.append(
      element("p", "draft-info", "هنوز Snapshot تأییدشده‌ای وجود ندارد."),
    );
    return section;
  }
  const list = element("ul", "stage-snapshots__list");
  snapshots.forEach((snapshot) => {
    const item = element("li", "stage-snapshots__item");
    item.append(
      element("strong", "", `نسخه ${snapshot.version}`),
      element("span", "", snapshot.name),
      element("span", "", formatPersianDate(snapshot.created_at)),
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
  const approve = element(
    "button",
    "button button--primary",
    "تأیید و عبور از G2",
  );
  const reject = element(
    "button",
    "button button--ghost",
    "رد و درخواست اصلاح",
  );
  panel.append(
    element("h2", "stage-form__legend", "بررسی آمادگی فنی G2"),
  );
  comment.className = corrections.className = "stage-form__control";
  comment.placeholder = "توضیح بازبین (اختیاری)";
  corrections.placeholder = "موارد اصلاح؛ هر مورد در یک خط";
  approve.type = reject.type = "button";
  approve.hidden = !canApprove;
  reject.hidden = !canReject;
  approve.addEventListener("click", async () => {
    approve.disabled = true;
    try {
      await stageService.approve(pilotId, 4, comment.value.trim());
      await reload(
        "Stage 4 و G2 تأیید شدند؛ پرونده آماده برداشت است و Stage 5 باز شد.",
      );
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
      feedback.textContent =
        "دلیل رد یا حداقل یک مورد اصلاح را وارد کنید.";
      return;
    }
    reject.disabled = true;
    try {
      await stageService.reject(pilotId, 4, { reason, correctionItems });
      await reload("Stage 4 برای اصلاح برگشت داده شد و G2 عبور نکرد.");
    } catch (error) {
      feedback.textContent = error.message;
      reject.disabled = false;
    }
  });
  actions.append(approve, reject);
  panel.append(comment, corrections, actions, feedback);
  return panel;
};

export const StageFourPage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canEdit = permissions.includes("forms.manage");
  const canSubmit = permissions.includes("checklists.manage");
  const canApprove = permissions.includes("gate_approval.approve");
  const canReject = permissions.includes("gate_approval.reject");

  const renderError = (message) => {
    const state = element("div", "error-state");
    const back = element("a", "button button--ghost", "بازگشت به جزئیات");
    const retry = element("button", "button button--primary", "تلاش مجدد");
    back.href = `#/pilots/${pilotId}`;
    retry.type = "button";
    retry.addEventListener("click", () => load());
    state.append(element("p", "error-state__message", message), retry, back);
    page.replaceChildren(state);
  };

  const load = async (notice = "") => {
    clearNavigationGuard();
    page.replaceChildren(
      element("p", "loading-state", "در حال دریافت فرم F02 و Stage 4..."),
    );
    try {
      const [pilot, f02, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        stageService.getF02(pilotId),
        stageService.getSnapshots(pilotId, 4),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 4);
      if (stage.status === "locked") {
        renderError("Stage 4 تا زمان تأیید Stage 3 قفل است.");
        return;
      }
      const gate = pilot.gates.find(({ code }) => code === "G2");
      const editable =
        ["open", "needs_revision"].includes(stage.status) && canEdit;
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const status = element(
        "span",
        "status-badge stage-workspace__status",
        `${LABELS[stage.status] ?? translateDisplayValue(stage.status, "وضعیت نامشخص")} — گیت ۲: ${translateDisplayValue(gate?.status ?? "locked", "وضعیت نامشخص")}`,
      );
      const form = StageFourForm({
        initialData: f02 ?? {},
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
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element(
          "span",
          "page-heading__eyebrow",
          `${pilot.code} — Stage 4 از ۱۹`,
        ),
        element(
          "h1",
          "page-heading__title",
          "راه‌اندازی در پلتفرم اصلی",
        ),
        element(
          "p",
          "draft-info",
          `${pilot.project.totalFloors} طبقه پروژه باید در پلتفرم اصلی کنترل شوند.`,
        ),
      );
      header.append(identity, status);
      page.replaceChildren(back, header, feedback, form.element);

      if (editable) {
        const actions = element("div", "stage-actions");
        const save = element(
          "button",
          "button button--ghost",
          "ذخیره فرم F02",
        );
        const submit = element(
          "button",
          "button button--primary",
          "ارسال برای بررسی G2",
        );
        save.type = submit.type = "button";
        submit.hidden = !canSubmit;
        const saveForm = async () => {
          save.disabled = true;
          await stageService.saveF02(pilot.id, form.getData());
          clearNavigationGuard();
          feedback.textContent = "فرم F02 و چک‌لیست Stage 4 ذخیره شد.";
          status.textContent = `${LABELS[stage.status] ?? translateDisplayValue(stage.status, "وضعیت نامشخص")} — گیت ۲: ${translateDisplayValue(gate?.status, "وضعیت نامشخص")}`;
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
            feedback.textContent =
              "تمام موارد قرمزشده چک‌لیست آمادگی فنی باید تأیید شوند.";
            return;
          }
          submit.disabled = true;
          try {
            await saveForm();
            await stageService.submit(pilot.id, 4);
            await load("Stage 4 برای بررسی G2 ارسال شد.");
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
      renderError(error.message ?? "دریافت Stage 4 انجام نشد.");
    }
  };
  load();
  return page;
};

import { stageService } from "../services/stageService.js";
import { formatPersianDateTime } from "../utils/dateFormatter.js";

export const stageElement = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

export const StageSnapshots = ({ snapshots, title = "نسخه‌های تأییدشده" }) => {
  const section = stageElement("section", "stage-snapshots");
  section.append(stageElement("h2", "stage-form__legend", title));
  if (!snapshots.length) {
    section.append(
      stageElement("p", "draft-info", "هنوز Snapshot تأییدشده‌ای وجود ندارد."),
    );
    return section;
  }
  const list = stageElement("ul", "stage-snapshots__list");
  snapshots.forEach((snapshot) => {
    const item = stageElement("li", "stage-snapshots__item");
    item.append(
      stageElement("strong", "", `نسخه ${snapshot.version}`),
      stageElement("span", "", snapshot.name),
      stageElement("span", "", formatPersianDateTime(snapshot.created_at)),
      stageElement("code", "", snapshot.content_hash),
    );
    list.append(item);
  });
  section.append(list);
  return section;
};

export const StageReviewPanel = ({
  pilotId,
  stageNumber,
  title,
  approveLabel,
  approvedNotice,
  rejectedNotice,
  canApprove,
  canReject,
  reload,
  onApproved,
}) => {
  const panel = stageElement("section", "stage-review");
  const comment = document.createElement("textarea");
  const corrections = document.createElement("textarea");
  const feedback = stageElement("p", "stage-actions__feedback");
  const actions = stageElement("div", "form-actions");
  const approve = stageElement(
    "button",
    "button button--primary",
    approveLabel,
  );
  const reject = stageElement(
    "button",
    "button button--ghost",
    "رد و درخواست اصلاح",
  );
  panel.append(stageElement("h2", "stage-form__legend", title));
  comment.className = corrections.className = "stage-form__control";
  comment.placeholder = "توضیح بازبین (اختیاری)";
  corrections.placeholder = "موارد اصلاح؛ هر مورد در یک خط";
  approve.type = reject.type = "button";
  approve.hidden = !canApprove;
  reject.hidden = !canReject;
  approve.addEventListener("click", async () => {
    approve.disabled = true;
    try {
      const result = await stageService.approve(
        pilotId,
        stageNumber,
        comment.value.trim(),
      );
      if (onApproved) {
        await onApproved(result);
      } else {
        await reload(approvedNotice);
      }
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
      await stageService.reject(pilotId, stageNumber, {
        reason,
        correctionItems,
      });
      await reload(rejectedNotice);
    } catch (error) {
      feedback.textContent = error.message;
      reject.disabled = false;
    }
  });
  actions.append(approve, reject);
  panel.append(comment, corrections, actions, feedback);
  return panel;
};

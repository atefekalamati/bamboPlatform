import { sessionStore } from "../app/sessionStore.js";
import { confirmDialog } from "../components/AppDialog.js";
import {
  buildFloorSlots,
  floorCreationPayload,
  getFloorRegistrationState,
  runFloorBulkOperation,
} from "../features/stages/stageThree.js";
import { getStageReviewAccess } from "../features/stages/stageReviewAccess.js";
import { dwgService } from "../services/dwgService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { formatPersianDateTime } from "../utils/dateFormatter.js";

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

const formatSize = (bytes) => {
  if (bytes < 1024) return `${bytes} بایت`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} کیلوبایت`;
  return `${(bytes / 1024 ** 2).toFixed(1)} مگابایت`;
};

const snapshotsView = (snapshots) => {
  const section = element("section", "stage-snapshots");
  section.append(element("h2", "stage-form__legend", "نسخه‌های تأییدشده Stage 3"));
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

const versionList = ({ versions, canDownload, feedback }) => {
  const list = element("ul", "dwg-versions");
  if (!versions.length) {
    list.append(element("li", "dwg-versions__empty", "فایل DWG ثبت نشده است."));
    return list;
  }
  versions
    .slice()
    .reverse()
    .forEach((version) => {
      const item = element("li", "dwg-version");
      const info = element("div", "dwg-version__info");
      info.append(
        element("strong", "", `V${String(version.version).padStart(2, "0")} — ${version.originalFilename}`),
        element(
          "span",
          "",
          `${formatSize(version.sizeBytes)} · ${formatPersianDateTime(version.uploadedAt)}`,
        ),
        element("code", "", version.sha256),
      );
      item.append(info);
      if (canDownload) {
        const download = element("button", "button button--ghost", "دانلود");
        download.type = "button";
        download.addEventListener("click", async () => {
          download.disabled = true;
          try {
            const result = await dwgService.download(version.id);
            const url = URL.createObjectURL(result.blob);
            const link = document.createElement("a");
            link.href = url;
            link.download = result.filename;
            link.click();
            URL.revokeObjectURL(url);
          } catch (error) {
            feedback.textContent = error.message;
          } finally {
            download.disabled = false;
          }
        });
        item.append(download);
      }
      list.append(item);
    });
  return list;
};

const floorCard = ({
  floor,
  versions,
  editable,
  canDownload,
  feedback,
  reload,
}) => {
  const card = element("article", "floor-card");
  const header = element("header", "floor-card__header");
  const identity = element("div", "floor-card__identity");
  const status = element(
    "span",
    `stage-status stage-status--${floor.hasValidDwg ? "approved" : "needs_revision"}`,
    floor.hasDwg
      ? `DWG نسخه ${floor.latestDwgVersion}`
      : floor.dwgReferenceConfirmed
        ? "تأییدشده در مرجع اصلی"
        : "بدون مدرک DWG",
  );
  identity.append(
    element("h3", "floor-card__title", `${floor.code} — ${floor.name}`),
    element(
      "span",
      "floor-card__meta",
      `ترتیب ${floor.levelOrder} · ${floor.floorType === "typical" ? "تیپ" : "غیرتیپ"}`,
    ),
  );
  header.append(identity, status);
  card.append(header);

  if (editable) {
    const controls = element("div", "floor-card__controls");
    const uploadRow = element("div", "dwg-upload");
    const input = document.createElement("input");
    const upload = element(
      "button",
      "button button--primary",
      floor.hasDwg ? "ثبت نسخه جدید" : "آپلود DWG",
    );
    input.type = "file";
    input.accept = ".dwg";
    upload.type = "button";
    upload.addEventListener("click", async () => {
      const file = input.files[0];
      input.setAttribute("aria-invalid", String(!file));
      if (!file) {
        feedback.textContent = `فایل DWG طبقه ${floor.code} را انتخاب کنید.`;
        return;
      }
      upload.disabled = true;
      try {
        await dwgService.upload(floor.id, file);
        await reload(`نسخه جدید DWG برای ${floor.code} ثبت شد.`);
      } catch (error) {
        feedback.textContent = error.message;
        upload.disabled = false;
      }
    });
    uploadRow.append(input, upload);
    const remove = element("button", "button button--danger", "حذف طبقه");
    remove.type = "button";
    remove.addEventListener("click", async () => {
      const detail = versions.length
        ? ` و ${versions.length} نسخه DWG آن`
        : "";
      if (
        !(await confirmDialog({
          title: "حذف طبقه",
          message: `طبقه ${floor.code}${detail} برای همیشه حذف شود؟ این عملیات قابل بازگشت نیست.`,
          confirmLabel: "حذف طبقه",
          confirmClassName: "button button--danger",
          triggerElement: remove,
        }))
      ) {
        return;
      }
      remove.disabled = true;
      try {
        await dwgService.deleteFloor(floor.id);
        await reload(`طبقه ${floor.code} حذف شد.`);
      } catch (error) {
        feedback.textContent = error.message;
        remove.disabled = false;
      }
    });
    controls.append(uploadRow, remove);
    card.append(controls);
  }

  const reference = element(
    "label",
    `dwg-reference${floor.dwgReferenceConfirmed ? " dwg-reference--confirmed" : ""}`,
  );
  const referenceCheckbox = document.createElement("input");
  const referenceText = element("span", "dwg-reference__text");
  referenceCheckbox.type = "checkbox";
  referenceCheckbox.dataset.navigationGuardIgnore = "true";
  referenceCheckbox.checked = floor.dwgReferenceConfirmed;
  referenceCheckbox.disabled = !editable;
  referenceText.append(
    element(
      "strong",
      "",
      "فایل DWG در مرجع اصلی موجود است یا فایل در اختیار من نیست.",
    ),
    element(
      "small",
      "",
      "با این تأیید، این طبقه بدون آپلود فایل برای عبور Stage 3 معتبر محسوب می‌شود.",
    ),
  );
  referenceCheckbox.addEventListener("change", async () => {
    const confirmed = referenceCheckbox.checked;
    if (
      confirmed &&
      !(await confirmDialog({
        title: "تأیید وجود فایل DWG",
        message: `تأیید می‌کنید فایل DWG طبقه ${floor.code} در مرجع اصلی وجود دارد یا در اختیار شما نیست؟`,
        triggerElement: referenceCheckbox,
      }))
    ) {
      referenceCheckbox.checked = false;
      return;
    }
    referenceCheckbox.disabled = true;
    try {
      await dwgService.setReferenceConfirmation(floor.id, confirmed);
      await reload(
        confirmed
          ? `وجود DWG مرجع برای ${floor.code} تأیید شد.`
          : `تأیید DWG مرجع برای ${floor.code} برداشته شد.`,
      );
    } catch (error) {
      referenceCheckbox.checked = !confirmed;
      referenceCheckbox.disabled = false;
      feedback.textContent = error.message;
    }
  });
  reference.append(referenceCheckbox, referenceText);
  card.append(reference);
  card.append(versionList({ versions, canDownload, feedback }));
  return card;
};

const createFloorsForm = ({
  pilotId,
  totalFloors,
  floors,
  versionsByFloorId,
  disabled,
  feedback,
  reload,
}) => {
  const container = element("section", "floor-definition");
  const slots = buildFloorSlots(totalFloors, floors);
  const editors = [];

  slots.forEach((slot) => {
    if (slot.floor) {
      editors.push({
        slot,
        floor: slot.floor,
        validateIdentity: () => true,
        ensureFloor: async () => slot.floor,
      });
      container.append(
        completedFloorCard({
          floor: slot.floor,
          versions: versionsByFloorId.get(slot.floor.id) ?? [],
        }),
      );
      return;
    }
    const card = element("article", "floor-card floor-card--draft");
    const heading = element("header", "floor-card__header");
    const nameLabel = element("label", "stage-form__field");
    const nameText = element("span", "stage-form__label", "نام طبقه");
    const name = document.createElement("input");
    const typeGroup = element("fieldset", "floor-card__type-options");
    const typeLegend = element("legend", "stage-form__label", "نوع طبقه");
    const typicalLabel = element("label", "floor-card__radio");
    const typical = document.createElement("input");
    const nonTypicalLabel = element("label", "floor-card__radio");
    const nonTypical = document.createElement("input");
    const evidence = element("section", "floor-card__evidence floor-card__evidence--compact");
    const file = document.createElement("input");
    const upload = element("button", "button button--primary", "انتخاب فایل و ثبت طبقه");
    const reference = element("label", "floor-card__radio floor-card__no-map");
    const referenceCheckbox = document.createElement("input");
    const cardFeedback = element("p", "floor-card__feedback");
    heading.append(
      element("span", "floor-card__index-label", `F-${slot.index}`),
    );
    name.className = "stage-form__control";
    name.placeholder = "نام طبقه را وارد کنید";
    name.required = true;
    name.disabled = disabled;
    typical.type = nonTypical.type = "radio";
    typical.name = nonTypical.name = `floor-type-${slot.index}`;
    typical.value = "typical";
    nonTypical.value = "non_typical";
    nonTypical.checked = true;
    typical.disabled = nonTypical.disabled = disabled;
    typicalLabel.append(typical, document.createTextNode("تیپ"));
    nonTypicalLabel.append(nonTypical, document.createTextNode("غیرتیپ"));
    typeGroup.append(typeLegend, typicalLabel, nonTypicalLabel);
    name.addEventListener("input", () => name.removeAttribute("aria-invalid"));
    nameLabel.append(nameText, name);
    file.type = "file";
    file.accept = ".dwg";
    file.className = "floor-card__file-input";
    file.disabled = disabled;
    upload.type = "button";
    upload.disabled = disabled;
    referenceCheckbox.type = "radio";
    referenceCheckbox.name = `floor-evidence-${slot.index}`;
    referenceCheckbox.value = "unavailable";
    referenceCheckbox.disabled = disabled;
    referenceCheckbox.dataset.navigationGuardIgnore = "true";
    reference.append(referenceCheckbox, document.createTextNode("نقشه در اختیار من نیست"));
    evidence.append(file, upload, reference, cardFeedback);

    const validateIdentity = () => {
      const valid = Boolean(name.value.trim());
      name.setAttribute("aria-invalid", String(!valid));
      if (!valid) {
        cardFeedback.textContent = "ابتدا نام این طبقه را وارد کنید.";
        name.focus();
      }
      return valid;
    };

    const createFloor = () =>
      dwgService.createFloor(
        pilotId,
        floorCreationPayload(
          slot,
          name.value,
          typical.checked ? typical.value : nonTypical.value,
        ),
      );

    editors.push({
      slot,
      get floor() {
        return null;
      },
      validateIdentity,
      ensureFloor: createFloor,
    });

    upload.addEventListener("click", async () => {
      if (!validateIdentity()) return;
      referenceCheckbox.checked = false;
      file.click();
    });

    file.addEventListener("change", async () => {
      const selectedFile = file.files[0];
      if (!selectedFile) return;
      upload.disabled = true;
      referenceCheckbox.disabled = true;
      upload.textContent = "در حال ثبت...";
      try {
        const createdFloor = await createFloor();
        await dwgService.upload(createdFloor.id, selectedFile);
        await reload(`اطلاعات و فایل DWG طبقه ${slot.index} ثبت شد.`);
      } catch (error) {
        await reload(`ثبت طبقه ${slot.index} متوقف شد: ${error.message}`);
      }
    });

    referenceCheckbox.addEventListener("change", async () => {
      if (!referenceCheckbox.checked) return;
      if (!validateIdentity()) {
        referenceCheckbox.checked = false;
        return;
      }
      if (
        !(await confirmDialog({
          title: "تأیید وجود نقشه DWG",
          message: `تأیید می‌کنید نقشه DWG طبقه ${name.value.trim()} در مرجع اصلی موجود است یا فایل در اختیار شما نیست؟`,
          triggerElement: referenceCheckbox,
        }))
      ) {
        referenceCheckbox.checked = false;
        return;
      }
      referenceCheckbox.disabled = true;
      upload.disabled = true;
      try {
        const createdFloor = await createFloor();
        await dwgService.setReferenceConfirmation(createdFloor.id, true);
        await reload(`اطلاعات و وجود نقشه طبقه ${slot.index} تأیید شد.`);
      } catch (error) {
        await reload(`ثبت طبقه ${slot.index} متوقف شد: ${error.message}`);
      }
    });

    card.append(heading, nameLabel, typeGroup, evidence);
    container.append(card);
  });

  if (!disabled && editors.length > 1) {
    const bulk = element("section", "stage3-bulk-evidence");
    const bulkCopy = element("div", "stage3-bulk-evidence__copy");
    const bulkActions = element("div", "stage3-bulk-evidence__actions");
    const unavailableAll = element(
      "button",
      "button button--ghost",
      "نقشه در اختیار نیست برای همه",
    );
    const uploadAll = element(
      "button",
      "button button--primary",
      "انتخاب یک DWG برای همه",
    );
    const sharedFile = document.createElement("input");
    const progress = element("p", "stage3-bulk-evidence__progress");
    sharedFile.type = "file";
    sharedFile.accept = ".dwg";
    sharedFile.hidden = true;
    unavailableAll.type = uploadAll.type = "button";
    bulkCopy.append(
      element("strong", "", "تعیین گروهی نقشه طبقات"),
      element(
        "small",
        "",
        "نام و نوع همه طبقات را وارد کنید؛ سپس یک وضعیت را برای همه اعمال کنید. گزینه‌های تکی هر کارت همچنان در دسترس است.",
      ),
    );

    const validateAll = () => {
      const invalid = editors.filter((editor) => !editor.validateIdentity());
      if (invalid.length) {
        feedback.textContent = `نام ${invalid.length} طبقه هنوز تکمیل نشده است.`;
        return false;
      }
      return true;
    };

    const setBusy = (busy) => {
      unavailableAll.disabled = busy;
      uploadAll.disabled = busy;
    };

    const executeBulk = async ({ actionLabel, operation }) => {
      setBusy(true);
      progress.textContent = `در حال ${actionLabel}: ۰ از ${editors.length}`;
      const result = await runFloorBulkOperation(
        editors,
        async (editor) => {
          const floor = await editor.ensureFloor();
          await operation(floor);
        },
        ({ completed, total }) => {
          progress.textContent = `در حال ${actionLabel}: ${completed} از ${total}`;
        },
      );
      const failureMessage = result.failed.length
        ? `؛ ${result.failed.length} طبقه ناموفق بود: ${result.failed
            .map(({ item }) => item.slot.code)
            .join("، ")}`
        : "";
      await reload(
        `${actionLabel} برای ${result.succeeded.length} طبقه انجام شد${failureMessage}.`,
      );
    };

    unavailableAll.addEventListener("click", async () => {
      if (!validateAll()) return;
      const confirmed = await confirmDialog({
        title: "تأیید گروهی وضعیت نقشه",
        message: `تأیید می‌کنید نقشه DWG برای هر ${editors.length} طبقه در اختیار شما نیست یا در مرجع اصلی موجود است؟`,
        confirmLabel: "تأیید برای همه طبقات",
        triggerElement: unavailableAll,
      });
      if (!confirmed) return;
      await executeBulk({
        actionLabel: "ثبت وضعیت نقشه",
        operation: (floor) => dwgService.setReferenceConfirmation(floor.id, true),
      });
    });

    uploadAll.addEventListener("click", () => {
      if (validateAll()) sharedFile.click();
    });

    sharedFile.addEventListener("change", async () => {
      const selectedFile = sharedFile.files[0];
      if (!selectedFile || !validateAll()) return;
      const confirmed = await confirmDialog({
        title: "آپلود یک نقشه برای همه طبقات",
        message: `فایل «${selectedFile.name}» برای هر ${editors.length} طبقه ثبت شود؟ برای طبقات دارای فایل، یک نسخه جدید ساخته می‌شود.`,
        confirmLabel: "آپلود برای همه طبقات",
        triggerElement: uploadAll,
      });
      if (!confirmed) {
        sharedFile.value = "";
        return;
      }
      await executeBulk({
        actionLabel: "آپلود فایل مشترک",
        operation: (floor) => dwgService.upload(floor.id, selectedFile),
      });
    });

    bulkActions.append(unavailableAll, uploadAll, sharedFile);
    bulk.append(bulkCopy, bulkActions, progress);
    container.prepend(bulk);
  }
  return container;
};

const completedFloorCard = ({ floor, versions }) => {
  const card = element("article", "floor-card floor-card--draft floor-card--completed");
  const heading = element("header", "floor-card__header");
  const nameLabel = element("label", "stage-form__field");
  const nameText = element("span", "stage-form__label", "نام طبقه");
  const name = document.createElement("input");
  const typeGroup = element("fieldset", "floor-card__type-options");
  const typeLegend = element("legend", "stage-form__label", "نوع طبقه");
  const typicalLabel = element("label", "floor-card__radio");
  const typical = document.createElement("input");
  const nonTypicalLabel = element("label", "floor-card__radio");
  const nonTypical = document.createElement("input");
  const evidence = element("section", "floor-card__evidence floor-card__evidence--compact");
  const latestVersion = versions.at(-1);
  const filename = element(
    "span",
    "floor-card__filename",
    latestVersion?.originalFilename ?? "فایل DWG آپلود نشده است",
  );
  const reference = element("label", "floor-card__radio floor-card__no-map");
  const referenceRadio = document.createElement("input");

  heading.append(
    element("span", "floor-card__index-label", `F-${floor.levelOrder + 1}`),
  );
  name.className = "stage-form__control";
  name.value = floor.name;
  name.disabled = true;
  nameLabel.append(nameText, name);
  typical.type = nonTypical.type = "radio";
  typical.name = nonTypical.name = `saved-floor-type-${floor.id}`;
  typical.checked = floor.floorType === "typical";
  nonTypical.checked = floor.floorType !== "typical";
  typical.disabled = nonTypical.disabled = true;
  typicalLabel.append(typical, document.createTextNode("تیپ"));
  nonTypicalLabel.append(nonTypical, document.createTextNode("غیرتیپ"));
  typeGroup.append(typeLegend, typicalLabel, nonTypicalLabel);
  filename.title = latestVersion?.originalFilename ?? "";
  referenceRadio.type = "radio";
  referenceRadio.checked = floor.dwgReferenceConfirmed;
  referenceRadio.disabled = true;
  reference.append(referenceRadio, document.createTextNode("نقشه در اختیار من نیست"));
  evidence.append(filename, reference);
  card.append(heading, nameLabel, typeGroup, evidence);
  return card;
};

const reviewPanel = ({ pilotId, canApprove, canReject, reload }) => {
  const panel = element("section", "stage-review");
  const comment = document.createElement("textarea");
  const corrections = document.createElement("textarea");
  const feedback = element("p", "stage-actions__feedback");
  const actions = element("div", "form-actions");
  const approve = element("button", "button button--primary", "تأیید Stage 3 و بازکردن Stage 4");
  const reject = element("button", "button button--ghost", "رد و درخواست اصلاح");
  panel.append(element("h2", "stage-form__legend", "بررسی DWG و طبقات"));
  comment.className = corrections.className = "stage-form__control";
  comment.placeholder = "توضیح بازبین (اختیاری)";
  corrections.placeholder = "موارد اصلاح؛ هر مورد در یک خط";
  approve.type = reject.type = "button";
  approve.hidden = !canApprove;
  reject.hidden = !canReject;
  approve.addEventListener("click", async () => {
    approve.disabled = true;
    try {
      await stageService.approve(pilotId, 3, comment.value.trim());
      await reload("Stage 3 تأیید شد و Stage 4 باز شد.");
    } catch (error) {
      feedback.textContent = error.message;
      approve.disabled = false;
    }
  });
  reject.addEventListener("click", async () => {
    const correctionItems = corrections.value.split("\n").map((item) => item.trim()).filter(Boolean);
    const reason = comment.value.trim();
    if (!reason && !correctionItems.length) {
      corrections.setAttribute("aria-invalid", "true");
      feedback.textContent = "دلیل رد یا حداقل یک مورد اصلاح را وارد کنید.";
      return;
    }
    reject.disabled = true;
    try {
      await stageService.reject(pilotId, 3, { reason, correctionItems });
      await reload("Stage 3 برای اصلاح برگشت داده شد.");
    } catch (error) {
      feedback.textContent = error.message;
      reject.disabled = false;
    }
  });
  actions.append(approve, reject);
  panel.append(comment, corrections, actions, feedback);
  return panel;
};

export const StageThreePage = ({ pilotId }) => {
  const page = element("div", "stage-workspace");
  const permissions = sessionStore.getCurrentUser()?.permissions ?? [];
  const canManageDwg = permissions.includes("dwg.manage");
  const canSubmit = permissions.includes("checklists.manage");
  const { canApprove, canReject } = getStageReviewAccess(
    sessionStore.getCurrentUser(),
    3,
  );

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
    page.replaceChildren(element("p", "loading-state", "در حال دریافت طبقات و فایل‌های DWG..."));
    try {
      const [pilot, floors, snapshots] = await Promise.all([
        pilotService.getPilotById(pilotId),
        dwgService.getFloors(pilotId),
        stageService.getSnapshots(pilotId, 3),
      ]);
      const stage = pilot.stages.find(({ number }) => number === 3);
      if (stage.status === "locked") {
        renderError("Stage 3 تا زمان تأیید Stage 2 قفل است.");
        return;
      }
      const versionsByFloorId = new Map(
        floors.map((floor) => [floor.id, floor.dwgVersions]),
      );
      const editable =
        ["open", "needs_revision"].includes(stage.status) && canManageDwg;
      const manageable =
        ["open", "needs_revision", "approved"].includes(stage.status) &&
        canManageDwg;
      const feedback = element("p", "stage-actions__feedback", notice);
      const back = element("a", "back-link", "بازگشت به جزئیات پرونده");
      const header = element("header", "stage-workspace__header");
      const identity = element("div", "stage-workspace__identity");
      const floorRegistration = getFloorRegistrationState(
        pilot.project.totalFloors,
        floors,
      );
      const complete =
        floorRegistration.isComplete && floors.every((floor) => floor.hasValidDwg);
      const completedFloorCount = floors.filter((floor) => floor.hasValidDwg).length;
      back.href = `#/pilots/${pilot.id}`;
      identity.append(
        element("span", "page-heading__eyebrow", `${pilot.code} — Stage 3 از ۱۹`),
        element("h1", "page-heading__title", "دریافت DWG و اطلاعات طبقات"),
        element(
          "p",
          "draft-info",
          `${floors.length} از ${pilot.project.totalFloors} طبقه ثبت شده · ${floors.filter((floor) => floor.hasValidDwg).length} مدرک DWG معتبر`,
        ),
      );
      header.append(
        identity,
        element("span", "status-badge stage-workspace__status", LABELS[stage.status] ?? stage.status),
      );
      const content = element("section", "floor-workspace");
      content.append(element("h2", "stage-form__legend", "طبقات پروژه"));
      content.append(
        element(
          "p",
          "floor-card__meta stage3-floor-count",
          `تعداد کل طبقات این پرونده: ${pilot.project.totalFloors}`,
        ),
      );
      const registrationStatus = element(
        "section",
        `stage3-registration-status${
          complete ? " stage3-registration-status--complete" : ""
        }`,
      );
      const registrationText = element("div", "stage3-registration-status__text");
      registrationText.append(
        element(
          "strong",
          "",
          complete
            ? "اطلاعات و نقشه همه طبقات تکمیل شده است"
            : "تکمیل اطلاعات و نقشه طبقات الزامی است",
        ),
        element(
          "small",
          "",
          complete
            ? "اکنون می‌توانید Stage 3 را برای بررسی ارسال کنید."
            : `${completedFloorCount} از ${floorRegistration.totalCount} طبقه کامل است؛ برای هر طبقه نام، نوع و فایل DWG یا تأیید وجود نقشه را ثبت کنید.`,
        ),
      );
      const registrationProgress = element("progress", "stage3-registration-status__progress");
      registrationProgress.max = Math.max(1, floorRegistration.totalCount);
      registrationProgress.value = completedFloorCount;
      registrationProgress.setAttribute(
        "aria-label",
        `پیشرفت تکمیل طبقات: ${completedFloorCount} از ${floorRegistration.totalCount}`,
      );
      registrationStatus.append(registrationText, registrationProgress);
      content.append(registrationStatus);
      const invalidReferenceFloors = floors.filter(
        (floor) => !floor.hasValidDwg,
      );
      if (["open", "needs_revision"].includes(stage.status)) {
        content.append(
          createFloorsForm({
            pilotId: pilot.id,
            totalFloors: pilot.project.totalFloors,
            floors,
            versionsByFloorId,
            disabled: !editable,
            feedback,
            reload: load,
          }),
        );
      } else {
        floors.forEach((floor, index) => {
          content.append(
            floorCard({
              floor,
              versions: versions[index],
              editable: manageable,
              canDownload: canManageDwg,
              feedback,
              reload: load,
            }),
          );
        });
      }
      page.replaceChildren(back, header, feedback, content);

      if (editable) {
        const actions = element("div", "stage-actions");
        const submit = element("button", "button button--primary", "ارسال Stage 3 برای بررسی");
        submit.type = "button";
        submit.hidden = !canSubmit;
        submit.disabled = !complete;
        submit.setAttribute(
          "aria-describedby",
          "stage3-submit-guidance",
        );
        const submitGuidance = element(
          "p",
          "stage-actions__hint",
          complete
            ? "پس از ارسال، مرحله برای بررسی مدیر پایلوت یا سوپرادمین آماده می‌شود."
            : "برای فعال‌شدن این دکمه، نام و نوع همه طبقات را تکمیل و برای هر طبقه فایل DWG یا تأیید وجود نقشه را ثبت کنید.",
        );
        submitGuidance.id = "stage3-submit-guidance";
        submit.addEventListener("click", async () => {
          if (!complete) {
            const missingFloors = pilot.project.totalFloors - floors.length;
            feedback.textContent = missingFloors > 0
              ? `ابتدا ${missingFloors} طبقه باقی‌مانده را ثبت کنید. آپلود DWG اجباری نیست.`
              : `برای این طبقات فایل آپلود نشده و تأیید مرجع هم ثبت نشده است: ${invalidReferenceFloors.map(({ code }) => code).join("، ")}`;
            content.classList.add("floor-workspace--invalid");
            return;
          }
          submit.disabled = true;
          try {
            await stageService.submit(pilot.id, 3);
            await load("Stage 3 برای بررسی ارسال شد.");
          } catch (error) {
            feedback.textContent = error.message;
            submit.disabled = false;
          }
        });
        actions.append(submitGuidance, submit);
        page.append(actions);
      }
      if (stage.status === "submitted" && (canApprove || canReject)) {
        page.append(reviewPanel({ pilotId: pilot.id, canApprove, canReject, reload: load }));
      }
      page.append(snapshotsView(snapshots));
    } catch (error) {
      renderError(error.message ?? "دریافت Stage 3 انجام نشد.");
    }
  };
  load();
  return page;
};

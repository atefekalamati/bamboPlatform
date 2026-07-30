import { sessionStore } from "../app/sessionStore.js";
import { dwgService } from "../services/dwgService.js";
import { pilotService } from "../services/pilotService.js";
import { stageService } from "../services/stageService.js";
import { formatPersianDate } from "../utils/dateFormatter.js";

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
      element("span", "", formatPersianDate(snapshot.created_at)),
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
          `${formatSize(version.sizeBytes)} · ${formatPersianDate(version.uploadedAt)}`,
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
        !window.confirm(
          `طبقه ${floor.code}${detail} برای همیشه حذف شود؟ این عملیات قابل بازگشت نیست.`,
        )
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
      !window.confirm(
        `تأیید می‌کنید فایل DWG طبقه ${floor.code} در مرجع اصلی وجود دارد یا در اختیار شما نیست؟`,
      )
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

const createFloorForm = ({ pilotId, nextIndex, disabled, feedback, reload }) => {
  const form = document.createElement("form");
  const code = document.createElement("input");
  const name = document.createElement("input");
  const order = document.createElement("input");
  const type = document.createElement("select");
  const submit = element("button", "button button--primary", "افزودن طبقه");
  const controls = [
    [code, "کد مانند F01"],
    [name, "نام طبقه"],
    [order, "ترتیب طبقه"],
  ];
  form.className = "floor-create";
  controls.forEach(([control, placeholder]) => {
    control.className = "stage-form__control";
    control.placeholder = placeholder;
    control.disabled = disabled;
  });
  code.value = `F${String(nextIndex).padStart(2, "0")}`;
  code.pattern = "F\\d{2,3}";
  name.required = true;
  order.type = "number";
  order.min = "-20";
  order.max = "500";
  order.value = String(nextIndex - 1);
  type.className = "stage-form__control";
  type.disabled = disabled;
  type.append(new Option("غیرتیپ", "non_typical"), new Option("تیپ", "typical"));
  submit.type = "submit";
  submit.disabled = disabled;
  form.append(code, name, order, type, submit);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const validCode = /^F\d{2,3}$/i.test(code.value.trim());
    const validName = name.value.trim().length > 0;
    code.setAttribute("aria-invalid", String(!validCode));
    name.setAttribute("aria-invalid", String(!validName));
    if (!validCode || !validName) {
      feedback.textContent = "فیلدهای قرمز طبقه را اصلاح کنید.";
      return;
    }
    submit.disabled = true;
    try {
      await dwgService.createFloor(pilotId, {
        code: code.value.trim(),
        name: name.value.trim(),
        levelOrder: order.value,
        floorType: type.value,
      });
      await reload("طبقه جدید ثبت شد.");
    } catch (error) {
      feedback.textContent = error.message;
      submit.disabled = false;
    }
  });
  return form;
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
      const versions = await Promise.all(
        floors.map((floor) => dwgService.getVersions(floor.id)),
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
      const complete =
        floors.length === pilot.project.totalFloors &&
        floors.every((floor) => floor.hasValidDwg);
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
      if (editable && floors.length < pilot.project.totalFloors) {
        content.append(
          createFloorForm({
            pilotId: pilot.id,
            nextIndex: floors.length + 1,
            disabled: false,
            feedback,
            reload: load,
          }),
        );
      }
      if (!floors.length) {
        content.append(element("p", "draft-info", "هنوز طبقه‌ای ثبت نشده است."));
      }
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
      page.replaceChildren(back, header, feedback, content);

      if (editable) {
        const actions = element("div", "stage-actions");
        const submit = element("button", "button button--primary", "ارسال Stage 3 برای بررسی");
        submit.type = "button";
        submit.hidden = !canSubmit;
        submit.addEventListener("click", async () => {
          if (!complete) {
            feedback.textContent =
              "برای تمام طبقات باید فایل DWG آپلود یا وجود آن در مرجع اصلی تأیید شود.";
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
        actions.append(submit);
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

import { Modal } from "./Modal.js";

const element = (tag, className, text = "") => {
  const node = document.createElement(tag);
  node.className = className;
  node.textContent = text;
  return node;
};

const getTriggerElement = (triggerElement) =>
  triggerElement ??
  (document.activeElement instanceof HTMLElement ? document.activeElement : null);

const createDialog = ({
  title,
  message,
  actions,
  triggerElement,
  onDismiss,
}) => {
  const content = element("div", "app-dialog");
  const description = element("p", "app-dialog__message", message);
  const actionBar = element("div", "app-dialog__actions");

  actions.forEach(({ label, className, onClick }) => {
    const button = element("button", className, label);
    button.type = "button";
    button.addEventListener("click", onClick);
    actionBar.append(button);
  });

  content.append(description, actionBar);
  return Modal({
    title,
    content,
    triggerElement: getTriggerElement(triggerElement),
    centered: true,
    onClose: onDismiss,
  });
};

export const confirmDialog = ({
  title = "تأیید عملیات",
  message,
  confirmLabel = "تأیید",
  cancelLabel = "لغو",
  confirmClassName = "button button--primary",
  triggerElement,
} = {}) =>
  new Promise((resolve) => {
    let settled = false;
    let modal;

    const finish = (accepted) => {
      if (settled) return;
      settled = true;
      modal.close();
      resolve(accepted);
    };

    modal = createDialog({
      title,
      message,
      triggerElement,
      onDismiss: () => {
        if (settled) return;
        settled = true;
        resolve(false);
      },
      actions: [
        {
          label: cancelLabel,
          className: "button button--ghost",
          onClick: () => finish(false),
        },
        {
          label: confirmLabel,
          className: confirmClassName,
          onClick: () => finish(true),
        },
      ],
    });
  });

export const alertDialog = ({
  title = "پیام سیستم",
  message,
  closeLabel = "بستن",
  triggerElement,
} = {}) =>
  new Promise((resolve) => {
    let settled = false;
    let modal;

    const finish = () => {
      if (settled) return;
      settled = true;
      modal.close();
      resolve();
    };

    modal = createDialog({
      title,
      message,
      triggerElement,
      onDismiss: () => {
        if (settled) return;
        settled = true;
        resolve();
      },
      actions: [
        {
          label: closeLabel,
          className: "button button--primary",
          onClick: finish,
        },
      ],
    });
  });

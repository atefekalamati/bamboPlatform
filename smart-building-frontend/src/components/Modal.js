const getFocusableElements = (container) =>
  container.querySelectorAll(
    'button:not([disabled]), input:not([disabled]), textarea:not([disabled]), select:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
  );

export const Modal = ({
  title,
  content,
  triggerElement,
  onClose,
  centered = false,
}) => {
  const overlay = document.createElement("div");
  const dialog = document.createElement("section");
  const header = document.createElement("header");
  const heading = document.createElement("h2");
  const closeButton = document.createElement("button");
  const titleId = `modal-title-${Date.now()}`;

  overlay.className = "modal-overlay";
  if (centered) overlay.classList.add("modal-overlay--centered");
  dialog.className = "modal";
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-modal", "true");
  dialog.setAttribute("aria-labelledby", titleId);
  header.className = "modal__header";
  heading.id = titleId;
  heading.className = "modal__title";
  heading.textContent = title;
  closeButton.className = "button button--ghost modal__close";
  closeButton.type = "button";
  closeButton.textContent = "بستن";
  closeButton.setAttribute("aria-label", "بستن پنجره");

  const close = () => {
    document.removeEventListener("keydown", handleKeydown);
    overlay.remove();
    triggerElement?.focus();
    onClose?.();
  };

  const handleKeydown = (event) => {
    if (event.key === "Escape") {
      close();
      return;
    }

    if (event.key !== "Tab") return;

    const focusableElements = [...getFocusableElements(dialog)];
    const firstElement = focusableElements[0];
    const lastElement = focusableElements.at(-1);

    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement?.focus();
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement?.focus();
    }
  };

  closeButton.addEventListener("click", close);
  overlay.addEventListener("mousedown", (event) => {
    if (event.target === overlay) close();
  });
  document.addEventListener("keydown", handleKeydown);

  header.append(heading, closeButton);
  dialog.append(header, content);
  overlay.append(dialog);
  document.body.append(overlay);
  getFocusableElements(dialog)[0]?.focus();

  return { close };
};

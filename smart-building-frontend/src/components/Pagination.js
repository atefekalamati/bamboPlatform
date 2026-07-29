const createButton = ({ label, isDisabled, onClick }) => {
  const button = document.createElement("button");

  button.className = "button button--ghost";
  button.type = "button";
  button.textContent = label;
  button.disabled = isDisabled;
  button.addEventListener("click", onClick);

  return button;
};

export const Pagination = ({ activePage, totalPages, onPageChange }) => {
  const navigation = document.createElement("nav");
  const pageStatus = document.createElement("span");
  const previousButton = createButton({
    label: "قبلی",
    isDisabled: activePage <= 1,
    onClick: () => onPageChange(activePage - 1),
  });
  const nextButton = createButton({
    label: "بعدی",
    isDisabled: activePage >= totalPages,
    onClick: () => onPageChange(activePage + 1),
  });

  navigation.className = "pagination";
  navigation.setAttribute("aria-label", "صفحه‌بندی");
  pageStatus.className = "pagination__status";
  pageStatus.textContent = `صفحه ${activePage} از ${totalPages}`;
  pageStatus.setAttribute("aria-live", "polite");
  navigation.append(previousButton, pageStatus, nextButton);

  return navigation;
};


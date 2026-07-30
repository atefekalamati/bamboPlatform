export const EmptyState = ({ title, description }) => {
  const container = document.createElement("section");
  const heading = document.createElement("h2");
  const message = document.createElement("p");

  container.className = "empty-state";
  container.setAttribute("aria-labelledby", "empty-state-title");

  heading.id = "empty-state-title";
  heading.className = "empty-state__title";
  heading.textContent = title;

  message.className = "empty-state__description";
  message.textContent = description;

  container.append(heading, message);

  return container;
};


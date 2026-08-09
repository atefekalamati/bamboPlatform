export const EmptyState = ({ title, description, actions = [] }) => {
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

  if (actions.length) {
    const actionBar = document.createElement("div");
    actionBar.className = "form-actions empty-state__actions";
    actions.forEach(({ label, className = "button button--ghost", onClick, href }) => {
      const action = document.createElement(href ? "a" : "button");
      action.className = className;
      action.textContent = label;
      if (href) action.href = href;
      else action.type = "button";
      if (onClick) action.addEventListener("click", onClick);
      actionBar.append(action);
    });
    container.append(actionBar);
  }

  return container;
};


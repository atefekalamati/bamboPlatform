export const AuthLayout = ({ content }) => {
  const layout = document.createElement("main");
  const brandPanel = document.createElement("section");
  const logo = document.createElement("img");
  const brandTitle = document.createElement("h1");
  const brandDescription = document.createElement("p");
  const formPanel = document.createElement("section");

  layout.id = "main-content";
  layout.className = "auth-layout";
  layout.tabIndex = -1;

  brandPanel.className = "auth-brand";
  logo.className = "auth-brand__logo";
  logo.src = "./src/assets/images/Persian Logo Final.svg";
  logo.alt = "BAMBO";
  brandTitle.className = "auth-brand__title";
  brandTitle.textContent = "مدیریت ساده و دقیق فرایند پایلوت";
  brandDescription.className = "auth-brand__description";
  brandDescription.textContent =
    "مراحل، چک‌لیست‌ها و تأییدهای هر پرونده را یکپارچه مدیریت کنید.";

  formPanel.className = "auth-panel";
  formPanel.setAttribute("aria-label", "ورود به سامانه");
  formPanel.append(content);

  brandPanel.append(logo, brandTitle, brandDescription);
  layout.append(brandPanel, formPanel);

  return layout;
};


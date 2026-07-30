import { EmptyState } from "../components/EmptyState.js";

export const DashboardPage = () => {
  const page = document.createElement("div");
  const headingGroup = document.createElement("header");
  const eyebrow = document.createElement("p");
  const title = document.createElement("h1");
  const description = document.createElement("p");

  page.className = "page";
  headingGroup.className = "page-heading";
  eyebrow.className = "page-heading__eyebrow";
  eyebrow.textContent = "BAMBO Pilot";
  title.className = "page-heading__title";
  title.textContent = "سامانه مدیریت فرایند پایلوت";
  description.className = "page-heading__description";
  description.textContent =
    "زیرساخت رابط کاربری آماده است. توسعه قابلیت‌ها پس از تأیید مرحله‌ای انجام می‌شود.";

  headingGroup.append(eyebrow, title, description);
  page.append(
    headingGroup,
    EmptyState({
      title: "هنوز پرونده‌ای نمایش داده نمی‌شود",
      description:
        "فهرست پرونده‌ها پس از نهایی‌شدن قرارداد API و تأیید فیچر Pilot List اضافه خواهد شد.",
    }),
  );

  return page;
};


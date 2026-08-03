const createBanner = () => {
  const banner = document.createElement("div");
  banner.className = "connection-status";
  banner.setAttribute("role", "status");
  banner.setAttribute("aria-live", "polite");
  banner.hidden = true;
  document.body.prepend(banner);
  return banner;
};

export const startConnectionStatus = () => {
  const banner = createBanner();
  const update = () => {
    banner.hidden = navigator.onLine;
    banner.textContent = navigator.onLine
      ? "اتصال اینترنت برقرار شد. عملیات ارسال‌نشده را دوباره بررسی کنید."
      : "اتصال اینترنت قطع است؛ هیچ تغییری تا برقراری مجدد ارسال نمی‌شود.";
    banner.classList.toggle("is-online", navigator.onLine);
    if (navigator.onLine) window.setTimeout(() => { banner.hidden = true; }, 4000);
  };
  window.addEventListener("online", update);
  window.addEventListener("offline", update);
  update();
  return () => {
    window.removeEventListener("online", update);
    window.removeEventListener("offline", update);
    banner.remove();
  };
};


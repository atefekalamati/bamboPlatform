const node = (tag, className = "", text = "") => { const item = document.createElement(tag); item.className = className; item.textContent = text; return item; };

export const PowerBIReport = ({ service, enabled }) => {
  const section = node("section", "dashboard-panel dashboard-powerbi");
  const header = node("header", "dashboard-panel__header");
  const title = node("h2", "dashboard-panel__title", "تحلیل مدیریتی");
  const actions = node("div", "dashboard-panel__actions");
  const refresh = node("button", "button button--ghost", "تازه‌سازی");
  const fullscreen = node("button", "button button--ghost", "تمام‌صفحه");
  const body = node("div", "powerbi-frame");
  let refreshTimer = null;

  refresh.type = fullscreen.type = "button";
  fullscreen.disabled = true;
  actions.append(refresh, fullscreen);
  header.append(title, actions);
  section.append(header, body);

  const showMessage = (message, kind = "info") => {
    body.replaceChildren(node("p", `dashboard-state dashboard-state--${kind}`, message));
    fullscreen.disabled = true;
  };

  const load = async () => {
    window.clearTimeout(refreshTimer);
    if (!enabled) {
      refresh.hidden = true;
      showMessage("برای مشاهده گزارش مدیریتی دسترسی reports.powerbi لازم است.", "no-access");
      return;
    }
    refresh.disabled = true;
    showMessage("در حال دریافت دسترسی امن گزارش…", "loading");
    try {
      const config = await service.getPowerBIEmbed();
      if (!config.embed_url) {
        showMessage("قرارداد بک‌اند هنوز Embed URL گزارش را ارائه نمی‌کند. داشبورد عملیاتی بدون وابستگی به Power BI فعال است.", "warning");
        return;
      }
      const iframe = document.createElement("iframe");
      iframe.className = "powerbi-frame__embed";
      iframe.title = "گزارش تحلیل مدیریتی BAMBO";
      iframe.src = config.embed_url;
      iframe.allowFullscreen = true;
      iframe.referrerPolicy = "strict-origin-when-cross-origin";
      body.replaceChildren(iframe);
      fullscreen.disabled = false;
      fullscreen.onclick = () => iframe.requestFullscreen?.();
      const expiry = new Date(config.expires_at).getTime() - Date.now() - 60_000;
      if (expiry > 0) refreshTimer = window.setTimeout(load, expiry);
    } catch (error) {
      showMessage(error.status === 503
        ? "سرویس Power BI در محیط فعلی پیکربندی نشده است."
        : error.status === 403 ? "دسترسی مشاهده گزارش مدیریتی را ندارید."
          : "بارگذاری Power BI انجام نشد؛ داشبورد عملیاتی همچنان قابل استفاده است.", "error");
    } finally { refresh.disabled = false; }
  };

  refresh.addEventListener("click", load);
  load();
  section.cleanup = () => window.clearTimeout(refreshTimer);
  return section;
};

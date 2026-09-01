import { request } from "./httpClient.js";

const queryString = (params = {}) => {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") query.set(key, value);
  });
  const serialized = query.toString();
  return serialized ? `?${serialized}` : "";
};

/** @typedef {"AUTH"|"PILOT"|"STAGE"|"MISSION"|"INCIDENT"|"SLA"|"COMMERCIAL"|"SYSTEM"} NotificationCategory */
/** @typedef {"LOW"|"NORMAL"|"HIGH"|"CRITICAL"} NotificationPriority */
/** @typedef {{id:string,type:string,category:NotificationCategory,priority:NotificationPriority,title:string,body:string,short_body:string|null,entity_type:string|null,entity_id:string|null,pilot_id:number|null,action_url:string|null,payload:Record<string, unknown>,is_read:boolean,created_at:string}} NotificationItem */

export const notificationService = Object.freeze({
  getNotifications: (params, options) => request(`/notifications${queryString(params)}`, options),
  getUnreadCount: () => request("/notifications/unread-count"),
  getNotification: (id) => request(`/notifications/${encodeURIComponent(id)}`),
  markAsRead: (id) => request(`/notifications/${encodeURIComponent(id)}/read`, { method: "PATCH" }),
  markAllAsRead: () => request("/notifications/read-all", { method: "POST" }),
  deleteNotification: (id) => request(`/notifications/${encodeURIComponent(id)}`, { method: "DELETE" }),
  getPreferences: () => request("/notification-preferences"),
  updatePreferences: (payload) => request("/notification-preferences", {
    method: "PUT",
    body: JSON.stringify(payload),
  }),
  getDeliveryLogs: () => request("/notifications/delivery-logs"),
});

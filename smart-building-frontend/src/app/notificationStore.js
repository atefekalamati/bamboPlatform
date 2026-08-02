import { notificationService } from "../services/notificationService.js";

const POLL_INTERVAL_MS = 30000;
const listeners = new Set();
const pendingReads = new Map();
let pollTimer = null;
let syncing = null;
let state = {
  items: [],
  unreadCount: 0,
  connectionStatus: "idle",
  lastSyncTime: null,
  error: null,
};

const emit = () => listeners.forEach((listener) => listener(state));
const update = (changes) => {
  state = { ...state, ...changes };
  emit();
};

const schedule = () => {
  window.clearTimeout(pollTimer);
  pollTimer = window.setTimeout(async () => {
    await notificationStore.sync().catch(() => null);
    schedule();
  }, POLL_INTERVAL_MS);
};

export const notificationStore = Object.freeze({
  getState: () => state,
  subscribe: (listener) => {
    listeners.add(listener);
    listener(state);
    return () => listeners.delete(listener);
  },
  sync: async () => {
    if (syncing) return syncing;
    update({ connectionStatus: "syncing", error: null });
    syncing = Promise.all([
      notificationService.getNotifications({ page: 1, page_size: 10 }),
      notificationService.getUnreadCount(),
    ])
      .then(([list, count]) => {
        update({
          items: list.items,
          unreadCount: count.unread_count,
          connectionStatus: "polling",
          lastSyncTime: new Date().toISOString(),
          error: null,
        });
        return state;
      })
      .catch((error) => {
        update({ connectionStatus: navigator.onLine ? "error" : "offline", error });
        throw error;
      })
      .finally(() => { syncing = null; });
    return syncing;
  },
  start: () => {
    notificationStore.sync().catch(() => null);
    schedule();
  },
  stop: () => {
    window.clearTimeout(pollTimer);
    pollTimer = null;
    pendingReads.clear();
    state = { items: [], unreadCount: 0, connectionStatus: "idle", lastSyncTime: null, error: null };
    emit();
  },
  markAsRead: async (id) => {
    if (pendingReads.has(id)) return pendingReads.get(id);
    const previous = state;
    const item = state.items.find((entry) => entry.id === id);
    if (item?.is_read) return item;
    if (item) {
      update({
        items: state.items.map((entry) => entry.id === id ? { ...entry, is_read: true } : entry),
        unreadCount: Math.max(0, state.unreadCount - 1),
      });
    }
    const operation = notificationService.markAsRead(id)
      .then((updated) => {
        if (item) update({ items: state.items.map((entry) => entry.id === id ? updated : entry) });
        return updated;
      })
      .catch((error) => {
        state = previous;
        emit();
        throw error;
      })
      .finally(() => pendingReads.delete(id));
    pendingReads.set(id, operation);
    return operation;
  },
  markAllAsRead: async () => {
    const previous = state;
    update({ items: state.items.map((item) => ({ ...item, is_read: true })), unreadCount: 0 });
    try {
      await notificationService.markAllAsRead();
    } catch (error) {
      state = previous;
      emit();
      throw error;
    }
  },
});

window.addEventListener("online", () => notificationStore.sync().catch(() => null));
window.addEventListener("offline", () => update({ connectionStatus: "offline" }));

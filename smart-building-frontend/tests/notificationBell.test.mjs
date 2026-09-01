import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("notification bell animates only for unread items and respects reduced motion", async () => {
  const component = await readFile(
    new URL("../src/components/NotificationCenter.js", import.meta.url),
    "utf8",
  );
  const styles = await readFile(
    new URL("../src/styles/notifications.css", import.meta.url),
    "utf8",
  );
  assert.match(component, /classList\.toggle\("notification-bell--active", hasUnread\)/);
  assert.match(styles, /notification-bell--active\[aria-expanded="false"\]/);
  assert.match(styles, /prefers-reduced-motion: reduce/);
});

test("notification center releases its subscription and document listener", async () => {
  const source = await readFile(new URL("../src/components/NotificationCenter.js", import.meta.url), "utf8");
  const store = await readFile(new URL("../src/app/notificationStore.js", import.meta.url), "utf8");
  assert.match(source, /root\.cleanup\s*=\s*\(\)\s*=>/);
  assert.match(source, /unsubscribe\(\)/);
  assert.match(source, /document\.removeEventListener\("click",\s*handleDocumentClick\)/);
  assert.match(store, /if \(isRunning\) return;/);
  assert.match(store, /syncController\?\.abort\(\)/);
  assert.match(store, /unreadCount: list\.unread_count/);
  assert.doesNotMatch(store, /notificationService\.getUnreadCount\(\)/);
  assert.match(store, /document\.hidden/);
});

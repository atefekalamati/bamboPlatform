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

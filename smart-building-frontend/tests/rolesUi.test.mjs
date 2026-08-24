import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

test("roles UI uses a compact selector and accessible permission tables", async () => {
  const page = await readFile(new URL("../src/pages/RolesPage.js", import.meta.url), "utf8");
  const styles = await readFile(new URL("../src/styles/roles.css", import.meta.url), "utf8");
  assert.match(page, /document\.createElement\("select"\)/);
  assert.match(page, /node\("table", "permission-table"\)/);
  assert.match(page, /aria-labelledby/);
  assert.doesNotMatch(page, /role-list__item/);
  assert.match(styles, /\.permission-table/);
  assert.match(styles, /@media \(max-width: 40rem\)/);
});

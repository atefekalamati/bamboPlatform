import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const stylesRoot = new URL("../src/styles/", import.meta.url);

test("loads the compact density layer after responsive styles", async () => {
  const index = await readFile(new URL("index.css", stylesRoot), "utf8");
  const responsiveIndex = index.indexOf('@import url("./responsive.css")');
  const compactIndex = index.indexOf('@import url("./compact.css")');

  assert.ok(responsiveIndex >= 0);
  assert.ok(compactIndex > responsiveIndex);
});

test("limits long collections without clipping the stage forms", async () => {
  const compact = await readFile(new URL("compact.css", stylesRoot), "utf8");

  assert.match(compact, /\.pilot-list,[\s\S]*max-block-size:/);
  assert.match(compact, /overflow-y:\s*auto/);
  assert.doesNotMatch(compact, /\.stage-form\s*\{[^}]*max-(?:block-)?size:/s);
});

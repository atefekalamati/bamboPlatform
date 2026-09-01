import assert from "node:assert/strict";
import test from "node:test";
import { readFile } from "node:fs/promises";
import {
  API_BASE_PATHS,
  API_PREFIXES,
} from "../src/config/apiRoutes.js";

test("keeps the existing legacy and versioned API prefix contract", () => {
  assert.equal(API_PREFIXES.legacy, "");
  assert.equal(API_PREFIXES.v1, "/api/v1");
  assert.equal(API_BASE_PATHS.dashboard, "/api/v1/dashboard");
  assert.equal(API_BASE_PATHS.reports, "/api/v1/reports");
});

test("versioned services consume the centralized base paths", async () => {
  const dashboard = await readFile(
    new URL("../src/services/dashboardService.js", import.meta.url),
    "utf8",
  );
  const reports = await readFile(
    new URL("../src/services/reportService.js", import.meta.url),
    "utf8",
  );

  assert.match(dashboard, /API_BASE_PATHS\.dashboard/);
  assert.match(reports, /API_BASE_PATHS\.reports/);
  assert.doesNotMatch(dashboard, /const DASHBOARD_BASE = "\/api\/v1/);
  assert.doesNotMatch(reports, /const BASE = "\/api\/v1/);
});

test("routing documentation covers every domain service", async () => {
  const document = await readFile(
    new URL("../../docs/frontend-api-routing-map.md", import.meta.url),
    "utf8",
  );
  const services = [
    "authService",
    "commercialService",
    "dashboardService",
    "dwgService",
    "evaluationService",
    "experienceService",
    "formService",
    "incidentService",
    "missionService",
    "notificationService",
    "pilotService",
    "preferenceService",
    "reportService",
    "roleService",
    "stageService",
    "userService",
  ];

  services.forEach((service) => assert.match(document, new RegExp(`\\b${service}\\b`)));
});

import { request } from "./httpClient.js";
import { buildPilotCreatePayload } from "../features/pilots/pilotCreation.js";

const mapStage = (stage, gates = []) => {
  const gate = gates.find(({ after_stage: afterStage }) => afterStage === stage.number);
  return {
    number: stage.number,
    title: stage.title,
    status: stage.status,
    latestVersion: stage.latest_version,
    submittedAt: stage.submitted_at,
    approvedAt: stage.approved_at,
    gate: gate
      ? {
          code: gate.code,
          title: gate.title,
          status: gate.status,
          passedAt: gate.passed_at,
        }
      : null,
  };
};

const mapPilot = (pilot) => ({
  id: pilot.id,
  code: pilot.code,
  pilotYear: pilot.pilot_year,
  projectNumber: pilot.project_number,
  projectSystemName: pilot.project_system_name,
  displayName: pilot.display_name,
  status: pilot.status,
  currentStage: pilot.current_stage,
  createdAt: pilot.created_at,
});

const mapPilotDetail = (pilot) => ({
  ...mapPilot(pilot),
  project: {
    id: pilot.project.id,
    name: pilot.project.name,
    systemName: pilot.project.system_name,
    displayName: pilot.project.display_name,
    totalFloors: pilot.project.total_floors,
    address: pilot.project.address,
    progressStage: pilot.project.progress_stage,
    customerNeed: pilot.project.customer_need,
    expectedValue: pilot.project.expected_value,
    owner: {
      id: pilot.project.owner.id,
      name: pilot.project.owner.name,
      decisionMakerName: pilot.project.owner.decision_maker_name,
      decisionMakerPosition: pilot.project.owner.decision_maker_position,
      primaryMobile: pilot.project.owner.primary_mobile,
    },
  },
  gates: pilot.gates.map((gate) => ({
    code: gate.code,
    title: gate.title,
    afterStage: gate.after_stage,
    status: gate.status,
    passedAt: gate.passed_at,
  })),
  stages: pilot.stages.map((stage) => mapStage(stage, pilot.gates)),
});

export const pilotService = Object.freeze({
  getPilots: async (options) => (await request("/pilots", options)).map(mapPilot),
  getPilotById: async (pilotId, options) =>
    mapPilotDetail(await request(`/pilots/${pilotId}`, options)),
  createPilot: async (values) =>
    mapPilotDetail(
      await request("/pilots", {
        method: "POST",
        body: JSON.stringify(buildPilotCreatePayload(values)),
      }),
    ),
});

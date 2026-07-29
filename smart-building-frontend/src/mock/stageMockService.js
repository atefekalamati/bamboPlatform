const MOCK_DELAY_MS = 500;
const drafts = new Map();

const createEmptyDraft = () => ({
  form: {
    ownerName: "",
    decisionMakerName: "",
    decisionMakerRole: "",
    phoneNumber: "",
    projectName: "",
    floorCount: "",
    address: "",
    projectPhase: "",
    customerNeed: "",
    expectedValue: "",
    caseOwner: "",
    deadline: "",
  },
  checklist: {},
  savedAt: null,
});

const cloneDraft = (draft) => structuredClone(draft);

export const stageMockService = Object.freeze({
  getStageDraft: (pilotId, stageNumber) =>
    new Promise((resolve) => {
      const key = `${pilotId}:${stageNumber}`;
      const draft = drafts.get(key) ?? createEmptyDraft();

      window.setTimeout(
        () =>
          resolve({
            success: true,
            message: "پیش‌نویس مرحله دریافت شد.",
            data: cloneDraft(draft),
          }),
        MOCK_DELAY_MS,
      );
    }),
  saveStageDraft: (pilotId, stageNumber, draftData) =>
    new Promise((resolve) => {
      const key = `${pilotId}:${stageNumber}`;
      const savedDraft = {
        ...cloneDraft(draftData),
        savedAt: new Date().toISOString(),
      };

      drafts.set(key, savedDraft);
      window.setTimeout(
        () =>
          resolve({
            success: true,
            message: "پیش‌نویس مرحله ذخیره شد.",
            data: cloneDraft(savedDraft),
          }),
        MOCK_DELAY_MS,
      );
    }),
});


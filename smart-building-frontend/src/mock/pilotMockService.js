const MOCK_DELAY_MS = 500;

const STAGE_NAMES = Object.freeze([
  "انتخاب پروژه مناسب برای پایلوت",
  "معرفی و موافقت",
  "دریافت DWG و اطلاعات",
  "راه‌اندازی در پلتفرم اصلی",
  "مأموریت",
  "آمادگی در محل",
  "برداشت Floor",
  "چند Floor",
  "وضعیت Upload در پلتفرم اصلی",
  "پردازش در پلتفرم اصلی",
  "اطلاع‌رسانی",
  "آموزش مالک",
  "موفقیت مشتری",
  "ادامه برداشت",
  "ارزیابی",
  "جلسه جمع‌بندی",
  "پیشنهاد تجاری",
  "پیگیری",
  "قرارداد یا بستن",
]);

const GATES_BY_STAGE = Object.freeze({
  2: "G1 پذیرش",
  4: "G2 آمادگی فنی",
  9: "G3 عملیات",
  13: "G4 تجربه",
  16: "G5 تجاری",
});

const pilots = Object.freeze([
  {
    id: "pilot-001",
    pilotCode: "PIL-1405-001",
    displayName: "شرکت آفتاب - سعادت‌آباد",
    ownerName: "شرکت آفتاب",
    status: "awaiting_documents",
    currentStage: 3,
    assigneeName: "رضا محمدی",
    dueAt: "2026-07-30T12:00:00Z",
    slaStatus: "at_risk",
  },
  {
    id: "pilot-002",
    pilotCode: "PIL-1405-002",
    displayName: "پروژه آرمان - نیاوران",
    ownerName: "گروه ساختمانی آرمان",
    status: "operations",
    currentStage: 7,
    assigneeName: "سارا احمدی",
    dueAt: "2026-07-29T08:00:00Z",
    slaStatus: "overdue",
  },
  {
    id: "pilot-003",
    pilotCode: "PIL-1405-003",
    displayName: "برج سپید - منطقه ۲۲",
    ownerName: "هلدینگ سپید",
    status: "evaluation",
    currentStage: 15,
    assigneeName: "مریم توکلی",
    dueAt: "2026-08-02T09:00:00Z",
    slaStatus: "on_track",
  },
  {
    id: "pilot-004",
    pilotCode: "PIL-1405-004",
    displayName: "مجتمع آریا - پاسداران",
    ownerName: "شرکت آریا سازه",
    status: "proposal_sent",
    currentStage: 18,
    assigneeName: "علی رضایی",
    dueAt: "2026-08-05T10:00:00Z",
    slaStatus: "on_track",
  },
  {
    id: "pilot-005",
    pilotCode: "PIL-1405-005",
    displayName: "خانه باغ مهر - لواسان",
    ownerName: "حمید مهران",
    status: "candidate",
    currentStage: 1,
    assigneeName: "نگار کاظمی",
    dueAt: "2026-07-29T15:00:00Z",
    slaStatus: "at_risk",
  },
]);

const matchesFilters = (pilot, search, status) => {
  const normalizedSearch = search.trim().toLocaleLowerCase("fa-IR");
  const matchesSearch =
    !normalizedSearch ||
    [pilot.pilotCode, pilot.displayName, pilot.ownerName].some((value) =>
      value.toLocaleLowerCase("fa-IR").includes(normalizedSearch),
    );
  const matchesStatus = !status || pilot.status === status;

  return matchesSearch && matchesStatus;
};

const createStages = (pilot) =>
  STAGE_NAMES.map((name, index) => {
    const number = index + 1;
    const status =
      number < pilot.currentStage
        ? "approved"
        : number === pilot.currentStage
          ? "in_progress"
          : "locked";

    return {
      number,
      name,
      status,
      assigneeName:
        status === "in_progress" ? pilot.assigneeName : "تعیین‌شده توسط فرایند",
      dueAt: status === "in_progress" ? pilot.dueAt : null,
      gateName: GATES_BY_STAGE[number] ?? null,
      hasSnapshot: status === "approved",
    };
  });

export const pilotMockService = Object.freeze({
  getPilots: ({ search = "", status = "", page = 1, pageSize = 20 } = {}) =>
    new Promise((resolve) => {
      const filteredPilots = pilots.filter((pilot) =>
        matchesFilters(pilot, search, status),
      );
      const startIndex = (page - 1) * pageSize;
      const items = filteredPilots.slice(startIndex, startIndex + pageSize);

      window.setTimeout(
        () =>
          resolve({
            success: true,
            message: "فهرست پرونده‌ها دریافت شد.",
            data: {
              items,
              page,
              pageSize,
              totalItems: filteredPilots.length,
              totalPages: Math.ceil(filteredPilots.length / pageSize),
            },
          }),
        MOCK_DELAY_MS,
      );
    }),
  getPilotById: (pilotId) =>
    new Promise((resolve, reject) => {
      const pilot = pilots.find((item) => item.id === pilotId);

      window.setTimeout(() => {
        if (!pilot) {
          reject(new Error("پرونده موردنظر پیدا نشد."));
          return;
        }

        resolve({
          success: true,
          message: "جزئیات پرونده دریافت شد.",
          data: {
            ...pilot,
            projectSystemName: `project-${Number(pilotId.split("-").at(-1))}`,
            stages: createStages(pilot),
          },
        });
      }, MOCK_DELAY_MS);
    }),
});

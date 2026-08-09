const ACTIONS = Object.freeze([
  { kind: "save", rank: 10, pattern: /ذخیره|ثبت پیش‌نویس|ثبت نتیجه|ثبت برنامه|ثبت تغییرات/ },
  { kind: "submit", rank: 20, pattern: /ارسال.*بررسی|ارسال مرحله|ارسال Stage/ },
  { kind: "approve", rank: 30, pattern: /تأیید/ },
  { kind: "next", rank: 40, pattern: /مرحله بعد|ورود به Stage|ادامه/ },
  { kind: "reject", rank: 50, pattern: /رد|درخواست اصلاح/ },
  { kind: "cancel", rank: 60, pattern: /انصراف|بازگشت/ },
]);

export const classifyStageAction = (label = "") =>
  ACTIONS.find(({ pattern }) => pattern.test(label.trim())) ?? null;

const actionElements = (container) =>
  [...container.children].filter((item) =>
    item.matches?.("button.button, a.button") && classifyStageAction(item.textContent),
  );

const normalizeContainer = (container) => {
  const actions = actionElements(container);
  if (actions.length < 1) return;
  const sorted = [...actions].sort(
    (left, right) =>
      classifyStageAction(left.textContent).rank - classifyStageAction(right.textContent).rank,
  );
  sorted.forEach((item) => {
    const action = classifyStageAction(item.textContent);
    item.dataset.stageAction = action.kind;
    item.title ||= `عملیات مرحله: ${item.textContent.trim()}`;
  });
  const lastIndex = Math.max(...actions.map((item) => [...container.children].indexOf(item)));
  const reference = container.children[lastIndex + 1] ?? null;
  const fragment = document.createDocumentFragment();
  sorted.forEach((item) => fragment.append(item));
  container.insertBefore(fragment, reference);
};

const wrapLooseActions = (page) => {
  const loose = [...page.children].filter((item) =>
    item.matches?.("button.button, a.button") && classifyStageAction(item.textContent),
  );
  if (!loose.length) return;
  const bar = document.createElement("div");
  bar.className = "stage-actions stage-actions--normalized";
  page.insertBefore(bar, loose[0]);
  loose.forEach((item) => bar.append(item));
};

export const installStageActionLayout = (page, route) => {
  if (!/^#\/pilots\/[^/]+\/stages\/\d+$/.test(route.split("?")[0])) return () => {};
  let queued = false;
  const normalize = () => {
    queued = false;
    observer.disconnect();
    wrapLooseActions(page);
    page.querySelectorAll(".stage-actions, .form-actions").forEach(normalizeContainer);
    observer.observe(page, { childList: true, subtree: true });
  };
  const schedule = () => {
    if (queued) return;
    queued = true;
    queueMicrotask(normalize);
  };
  const observer = new MutationObserver(schedule);
  observer.observe(page, { childList: true, subtree: true });
  schedule();
  return () => observer.disconnect();
};

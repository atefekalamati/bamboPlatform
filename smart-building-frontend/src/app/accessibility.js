const LIVE_REGION_SELECTORS = [
  ".stage-actions__feedback",
  ".form-feedback",
  ".error-state__message",
  ".loading-state",
];

const enhanceLiveRegion = (node) => {
  if (!(node instanceof Element)) return;
  LIVE_REGION_SELECTORS.forEach((selector) => {
    const regions = node.matches(selector)
      ? [node]
      : [...node.querySelectorAll(selector)];
    regions.forEach((region) => {
      const isError = region.matches(".error-state__message") || region.dataset.type === "error";
      if (!region.hasAttribute("role")) region.setAttribute("role", isError ? "alert" : "status");
      if (!region.hasAttribute("aria-live")) region.setAttribute("aria-live", isError ? "assertive" : "polite");
      region.setAttribute("aria-atomic", "true");
    });
  });
};

export const startLiveRegionEnhancements = (root = document.body) => {
  enhanceLiveRegion(root);
  const observer = new MutationObserver((records) => {
    records.forEach((record) => {
      record.addedNodes.forEach((node) => enhanceLiveRegion(node));
      if (record.type === "attributes") enhanceLiveRegion(record.target);
    });
  });
  observer.observe(root, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ["data-type"],
  });
  return () => observer.disconnect();
};

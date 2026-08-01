const PERSIAN_DIGITS = Object.freeze([
  "۰",
  "۱",
  "۲",
  "۳",
  "۴",
  "۵",
  "۶",
  "۷",
  "۸",
  "۹",
]);

const LOCALIZED_ATTRIBUTES = Object.freeze([
  "aria-label",
  "aria-valuetext",
  "placeholder",
  "title",
]);

const EXCLUDED_CONTENT_SELECTOR = "script, style, code, pre, textarea";

export const toPersianDigits = (value) =>
  String(value).replace(/[0-9]/g, (digit) => PERSIAN_DIGITS[Number(digit)]);

const localizeTextNode = (textNode) => {
  if (textNode.parentElement?.closest(EXCLUDED_CONTENT_SELECTOR)) return;

  const localizedText = toPersianDigits(textNode.nodeValue ?? "");
  if (localizedText !== textNode.nodeValue) textNode.nodeValue = localizedText;
};

const localizeElementAttributes = (element) => {
  LOCALIZED_ATTRIBUTES.forEach((attribute) => {
    if (!element.hasAttribute(attribute)) return;

    const value = element.getAttribute(attribute) ?? "";
    const localizedValue = toPersianDigits(value);
    if (localizedValue !== value) element.setAttribute(attribute, localizedValue);
  });
};

export const localizePersianDigits = (root) => {
  if (!root) return;

  if (root.nodeType === Node.TEXT_NODE) {
    localizeTextNode(root);
    return;
  }

  if (!(root instanceof Element) && !(root instanceof Document)) return;

  if (root instanceof Element) localizeElementAttributes(root);

  const elementWalker = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT);
  while (elementWalker.nextNode()) localizeElementAttributes(elementWalker.currentNode);

  const textWalker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
  while (textWalker.nextNode()) localizeTextNode(textWalker.currentNode);
};

export const startPersianDigitLocalization = (root = document.documentElement) => {
  localizePersianDigits(root);

  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === "characterData") {
        localizeTextNode(mutation.target);
        return;
      }

      if (mutation.type === "attributes") {
        localizeElementAttributes(mutation.target);
        return;
      }

      mutation.addedNodes.forEach(localizePersianDigits);
    });
  });

  observer.observe(root, {
    attributeFilter: LOCALIZED_ATTRIBUTES,
    attributes: true,
    characterData: true,
    childList: true,
    subtree: true,
  });

  return () => observer.disconnect();
};

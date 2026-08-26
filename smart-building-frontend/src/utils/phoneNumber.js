const PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹";
const ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩";

export const normalizeDigits = (value) =>
  [...value]
    .map((character) => {
      const persianIndex = PERSIAN_DIGITS.indexOf(character);
      const arabicIndex = ARABIC_DIGITS.indexOf(character);

      if (persianIndex >= 0) return String(persianIndex);
      if (arabicIndex >= 0) return String(arabicIndex);

      return character;
    })
    .join("");

export const normalizePhoneNumber = (value) =>
  normalizeDigits(String(value ?? "")).replace(/[^\d+]/g, "");

export const toInternationalPhoneNumber = (value) => {
  if (/[*•xX]/.test(String(value ?? ""))) return "";
  const normalized = normalizePhoneNumber(value);
  if (!normalized) return "";

  let international = normalized;
  if (international.startsWith("0098")) international = `+98${international.slice(4)}`;
  else if (international.startsWith("98")) international = `+${international}`;
  else if (international.startsWith("0")) international = `+98${international.slice(1)}`;
  else if (!international.startsWith("+")) international = `+98${international}`;

  return /^\+[1-9]\d{7,14}$/.test(international) ? international : "";
};

export const isCallablePhoneNumber = (value) => Boolean(toInternationalPhoneNumber(value));

export const isValidIranianMobile = (value) => /^09\d{9}$/.test(value);

export const maskPhoneNumber = (value) => {
  if (value.length < 7) return value;

  return `${value.slice(0, 4)}***${value.slice(-4)}`;
};


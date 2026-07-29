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
  normalizeDigits(value).replace(/[^\d+]/g, "");

export const isValidIranianMobile = (value) => /^09\d{9}$/.test(value);

export const maskPhoneNumber = (value) => {
  if (value.length < 7) return value;

  return `${value.slice(0, 4)}***${value.slice(-4)}`;
};


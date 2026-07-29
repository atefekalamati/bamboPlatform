const persianDateFormatter = new Intl.DateTimeFormat("fa-IR-u-ca-persian", {
  year: "numeric",
  month: "long",
  day: "numeric",
});

export const formatPersianDate = (isoDate) => {
  if (!isoDate) return "ثبت نشده";

  const date = new Date(isoDate);

  return Number.isNaN(date.getTime())
    ? "تاریخ نامعتبر"
    : persianDateFormatter.format(date);
};


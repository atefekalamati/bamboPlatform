export const buildUserNamePatch = ({ currentDisplayName = "", displayName = "" }) => {
  const normalizedName = displayName.trim();
  const errors = {};

  if (normalizedName.length < 2 || normalizedName.length > 120) {
    errors.displayName = "نام باید بین ۲ تا ۱۲۰ کاراکتر باشد.";
  }

  const payload = {};
  if (normalizedName !== currentDisplayName.trim()) {
    payload.display_name = normalizedName;
  }

  if (!Object.keys(errors).length && !Object.keys(payload).length) {
    errors.form = "تغییری برای ذخیره ثبت نشده است.";
  }

  return { payload, errors };
};

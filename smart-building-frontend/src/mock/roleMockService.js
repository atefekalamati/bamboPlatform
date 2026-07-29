const ROLES = Object.freeze([
  { id: "role-pilot-manager", name: "مدیر پایلوت" },
  { id: "role-sales", name: "جذب/فروش" },
  { id: "role-setup", name: "مسئول راه‌اندازی" },
  { id: "role-operations", name: "هماهنگ‌کننده عملیات" },
  { id: "role-surveyor", name: "کارشناس برداشت" },
  { id: "role-support", name: "پشتیبانی/آموزش" },
  { id: "role-success", name: "موفقیت مشتری" },
  { id: "role-technical", name: "تیم فنی" },
  { id: "role-product", name: "مدیر محصول" },
]);

export const roleMockService = Object.freeze({
  getRoles: async () => ({
    success: true,
    message: "فهرست نقش‌ها دریافت شد.",
    data: { items: ROLES },
  }),
});


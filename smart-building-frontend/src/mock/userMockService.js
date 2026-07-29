const MOCK_DELAY_MS = 500;

const users = [
  {
    id: "usr-001",
    fullName: "علی رضایی",
    phoneNumber: "09121234567",
    roleId: "role-pilot-manager",
    roleName: "مدیر پایلوت",
    status: "active",
  },
  {
    id: "usr-002",
    fullName: "سارا احمدی",
    phoneNumber: "09123456789",
    roleId: "role-operations",
    roleName: "هماهنگ‌کننده عملیات",
    status: "active",
  },
  {
    id: "usr-003",
    fullName: "محمد کریمی",
    phoneNumber: "09351234567",
    roleId: "role-surveyor",
    roleName: "کارشناس برداشت",
    status: "locked",
  },
  {
    id: "usr-004",
    fullName: "مریم توکلی",
    phoneNumber: "09191234567",
    roleId: "role-success",
    roleName: "موفقیت مشتری",
    status: "inactive",
  },
];

const includesSearchTerm = (user, searchTerm) => {
  if (!searchTerm) return true;

  const normalizedSearchTerm = searchTerm.trim().toLocaleLowerCase("fa-IR");

  return [user.fullName, user.phoneNumber, user.roleName].some((value) =>
    value.toLocaleLowerCase("fa-IR").includes(normalizedSearchTerm),
  );
};

export const userMockService = Object.freeze({
  getUsers: ({ search = "", page = 1, pageSize = 20 } = {}) =>
    new Promise((resolve) => {
      const filteredUsers = users.filter((user) =>
        includesSearchTerm(user, search),
      );
      const startIndex = (page - 1) * pageSize;
      const paginatedUsers = filteredUsers.slice(
        startIndex,
        startIndex + pageSize,
      );
      const totalPages = Math.ceil(filteredUsers.length / pageSize);

      window.setTimeout(
        () =>
          resolve({
            success: true,
            message: "فهرست کاربران دریافت شد.",
            data: {
              items: paginatedUsers,
              page,
              pageSize,
              totalItems: filteredUsers.length,
              totalPages,
            },
          }),
        MOCK_DELAY_MS,
      );
    }),
  createUser: (userData) =>
    new Promise((resolve, reject) => {
      window.setTimeout(() => {
        const isDuplicate = users.some(
          (user) => user.phoneNumber === userData.phoneNumber,
        );

        if (isDuplicate) {
          reject(new Error("کاربری با این شماره موبایل وجود دارد."));
          return;
        }

        const createdUser = {
          id: `mock-user-${crypto.randomUUID()}`,
          ...userData,
        };

        users = [createdUser, ...users];
        resolve({
          success: true,
          message: "کاربر با موفقیت ایجاد شد.",
          data: createdUser,
        });
      }, MOCK_DELAY_MS);
    }),
  updateUser: (userId, userData) =>
    new Promise((resolve, reject) => {
      window.setTimeout(() => {
        const userIndex = users.findIndex((user) => user.id === userId);
        const isDuplicate = users.some(
          (user) =>
            user.id !== userId && user.phoneNumber === userData.phoneNumber,
        );

        if (userIndex < 0) {
          reject(new Error("کاربر موردنظر پیدا نشد."));
          return;
        }

        if (isDuplicate) {
          reject(new Error("کاربری با این شماره موبایل وجود دارد."));
          return;
        }

        const updatedUser = { ...users[userIndex], ...userData };
        users = users.map((user) => (user.id === userId ? updatedUser : user));
        resolve({
          success: true,
          message: "اطلاعات کاربر به‌روزرسانی شد.",
          data: updatedUser,
        });
      }, MOCK_DELAY_MS);
    }),
});

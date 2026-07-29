const MOCK_DELAY_MS = 500;

const createSuccessResponse = (message) => ({
  success: true,
  message,
  data: {},
});

const resolveAfterDelay = (response) =>
  new Promise((resolve) => {
    window.setTimeout(() => resolve(response), MOCK_DELAY_MS);
  });

export const authMockService = Object.freeze({
  requestOtp: () =>
    resolveAfterDelay(createSuccessResponse("کد ورود ارسال شد.")),
  verifyOtp: () =>
    resolveAfterDelay(createSuccessResponse("ورود با موفقیت انجام شد.")),
});


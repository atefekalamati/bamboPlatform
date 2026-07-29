import { APP_CONFIG } from "../config/appConfig.js";
import { stageMockService } from "../mock/stageMockService.js";

const missingContractError = () =>
  Promise.reject(
    new Error("قرارداد API پیش‌نویس مرحله هنوز توسط Backend تعریف نشده است."),
  );

const stageApiService = Object.freeze({
  getStageDraft: missingContractError,
  saveStageDraft: missingContractError,
});

export const stageService = APP_CONFIG.useMockApi
  ? stageMockService
  : stageApiService;


import axios, { AxiosError } from 'axios';

// Respect VITE_API_BASE_URL if configured, otherwise fallback to standard '/api' proxy
const baseURL = import.meta.env.VITE_API_BASE_URL || '/api';

type ApiErrorPayload = {
  detail?: string | Record<string, unknown> | Array<Record<string, unknown>>;
  message?: string;
  status?: string;
  error?: {
    code?: string;
    message?: string;
    details?: unknown[];
  };
};

const extractValidationMessage = (details: unknown): string | null => {
  if (!Array.isArray(details) || details.length === 0) {
    return null;
  }

  const first = details[0];
  if (typeof first === 'string') {
    return first;
  }

  if (first && typeof first === 'object') {
    const candidate = first as { msg?: string; message?: string; loc?: unknown[] };
    if (candidate.msg) return candidate.msg;
    if (candidate.message) return candidate.message;
  }

  return null;
};

export const apiClient = axios.create({
  baseURL,
  timeout: 25000,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorPayload>) => {
    let message = 'An unexpected network error occurred';

    const payload = error.response?.data;
    if (payload) {
      if (typeof payload === 'string') {
        message = payload;
      } else if (payload.error?.message) {
        message = payload.error.message;
        const detailMessage = extractValidationMessage(payload.error.details);
        if (detailMessage) {
          message = `${message}: ${detailMessage}`;
        }
      } else if (typeof payload.detail === 'string') {
        message = payload.detail;
      } else if (payload.message) {
        message = payload.message;
      } else if (Array.isArray(payload.detail) && payload.detail.length > 0) {
        const firstDetail = payload.detail[0] as { msg?: string; message?: string };
        message = firstDetail?.msg || firstDetail?.message || message;
      } else if (payload.detail && typeof payload.detail === 'object') {
        const detailObj = payload.detail as { message?: string; msg?: string };
        message = detailObj.message || detailObj.msg || message;
      }
    }

    if (error.message && !message.includes(error.message)) {
      message = error.message;
    }

    return Promise.reject(new Error(message));
  }
);

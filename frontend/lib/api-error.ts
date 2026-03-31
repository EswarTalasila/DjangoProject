export type ApiErrorData =
  | string
  | {
      detail?: unknown;
      non_field_errors?: unknown;
      errors?: unknown;
      [key: string]: unknown;
    }
  | undefined;

export type ApiError = {
  response?: {
    data?: ApiErrorData;
  };
};

export function isApiErrorRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

import api from '@/lib/api';

type BaseExportParams = {
  identifiable?: boolean;
};

export type RosterExportParams = BaseExportParams & {
  status?: string;
};

export type CourseSubmissionsExportParams = BaseExportParams & {
  startDate?: string;
  endDate?: string;
  category?: string;
  assessmentId?: number;
  assignmentId?: number;
  status?: string;
  includeAnswers?: boolean;
};

export type ExportDownload = {
  blob: Blob;
  filename: string;
};

function parseFilename(contentDisposition: string | undefined, fallback: string): string {
  if (!contentDisposition) return fallback;
  const match = contentDisposition.match(/filename="?([^"]+)"?/i);
  return match?.[1] || fallback;
}

/** Fetch a CSV export from the given API path and return the blob with its filename. */
async function getCsv(
  path: string,
  params: Record<string, string | number | boolean | undefined>,
  fallbackFilename: string,
): Promise<ExportDownload> {
  const response = await api.get(path, {
    params,
    responseType: 'blob',
  });

  const filename = parseFilename(response.headers['content-disposition'], fallbackFilename);
  return { blob: response.data, filename };
}

/** GET /exports/courses/:id/roster — Download a course roster as CSV. */
export async function downloadCourseRoster(
  courseId: number,
  params: RosterExportParams = {},
): Promise<ExportDownload> {
  return getCsv(
    `/exports/courses/${courseId}/roster`,
    params,
    `roster-${courseId}.csv`,
  );
}

/** GET /exports/courses/:id/submissions — Download course submissions as CSV. */
export async function downloadCourseSubmissions(
  courseId: number,
  params: CourseSubmissionsExportParams = {},
): Promise<ExportDownload> {
  return getCsv(
    `/exports/courses/${courseId}/submissions`,
    params,
    `submissions-course-${courseId}.csv`,
  );
}

/** Extract a human-readable error message from an export failure response (handles Blob and JSON bodies). */
export async function extractExportErrorMessage(error: unknown): Promise<string> {
  const defaultMessage = 'Export failed. Please check filters and permissions.';
  if (!error || typeof error !== 'object') return defaultMessage;
  const maybeResponse = (error as { response?: { data?: unknown } }).response;
  if (!maybeResponse) return defaultMessage;
  const data = maybeResponse.data;

  if (data instanceof Blob) {
    try {
      const text = await data.text();
      const parsed = JSON.parse(text) as { detail?: string };
      return parsed.detail || defaultMessage;
    } catch {
      return defaultMessage;
    }
  }

  if (typeof data === 'object' && data !== null && 'detail' in data) {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === 'string' && detail.trim()) return detail;
  }

  return defaultMessage;
}

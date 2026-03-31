import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Extract a user-friendly error message from an Axios error response.
 *  Accepts an optional fallback that replaces the default "Unexpected error." */
export function toErrorMessage(error: unknown, fallback = 'Unexpected error.'): string {
  return (
    (error as { response?: { data?: { detail?: string } } })?.response?.data
      ?.detail || fallback
  );
}

// -- Date / score formatting helpers --

/** Format an ISO date string to a full locale date+time string (e.g. "3/30/2026, 2:15:00 PM"). */
export function formatDate(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

/** Format an ISO date string to a short en-US date (e.g. "Mar 30, 2026"). */
export function formatShortDate(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/** Format an ISO date string to en-US date+time (e.g. "Mar 30, 2026, 2:15 PM"). */
export function formatDateTime(value: string | null): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

/** Format a numeric score for display (integers stay whole, decimals trimmed). */
export function formatScore(value: number | null | undefined): string {
  if (value == null) return '-';
  if (Number.isInteger(value)) return String(value);
  return value.toFixed(2).replace(/\.?0+$/, '');
}

/** Trigger a browser file download from a Blob. */
export function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

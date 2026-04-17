/**
 * Shared axios instance with automatic token refresh and 401 redirect.
 *
 * - Attaches credentials on every request.
 * - On 401, attempts a silent token exchange via /auth/token-exchanges.
 * - If the refresh also fails, clears the user cookie and redirects to /login.
 * - Public endpoints (login, registration, password reset) skip the refresh cycle.
 *
 * Browser API base: always relative "/api/v1" (resolved by nginx/proxy).
 * Server-side code resolves an absolute proxy URL separately in auth-session.ts.
 */
import axios from 'axios';
import Cookies from 'js-cookie';
import type { AxiosRequestConfig } from 'axios';

export type ApiRequestOptions = AxiosRequestConfig & {
  suppressAuthRedirect?: boolean;
};

const API_URL = (process.env.NEXT_PUBLIC_API_URL || '/api/v1').replace(/\/$/, '');

const PUBLIC_ENDPOINTS = new Set([
  '/auth/sessions',
  '/auth/sessions/oauth',
  '/registration/code-validations',
  '/registration/accounts',
  '/auth/reset-code-validations',
  '/auth/password-resets',
]);

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

function normalizeRequestPath(url?: string): string {
  if (!url) return '';
  const withoutQuery = url.split('?')[0];
  return withoutQuery.endsWith('/') && withoutQuery !== '/'
    ? withoutQuery.slice(0, -1)
    : withoutQuery;
}

// Response Interceptor: Handle 401 (Unauthorized)
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config ?? {};
    const path = normalizeRequestPath(originalRequest.url);
    const retryState = originalRequest as { _retry?: boolean; suppressAuthRedirect?: boolean };
    const suppressAuthRedirect = retryState.suppressAuthRedirect === true;

    if (
      error.response?.status === 401 &&
      !retryState._retry &&
      path !== '/auth/token-exchanges' &&
      !PUBLIC_ENDPOINTS.has(path)
    ) {
      retryState._retry = true;
      try {
        await api.post('/auth/token-exchanges', {});
        return api(originalRequest);
      } catch {
        Cookies.remove('user_name');
        if (
          !suppressAuthRedirect &&
          typeof window !== 'undefined' &&
          !window.location.pathname.includes('/login')
        ) {
          window.location.href = '/login';
        }
      }
    }

    if (error.response?.status === 401) {
      Cookies.remove('user_name');
      if (
        !suppressAuthRedirect &&
        typeof window !== 'undefined' &&
        !window.location.pathname.includes('/login')
      ) {
        window.location.href = '/login';
      }
    }

    return Promise.reject(error);
  }
);

export default api;

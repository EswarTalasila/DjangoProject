import axios from 'axios';
import Cookies from 'js-cookie';

function resolveApiUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  try {
    const url = new URL(configured);
    if (
      typeof window !== 'undefined' &&
      url.hostname === 'localhost' &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1'
    ) {
      url.hostname = 'backend';
    }
    return url.toString().replace(/\/$/, '');
  } catch {
    return configured.replace(/\/$/, '');
  }
}

const API_URL = resolveApiUrl();
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

api.interceptors.request.use((config) => {
  const path = normalizeRequestPath(config.url);
  if (PUBLIC_ENDPOINTS.has(path)) {
    return config;
  }

  const token = Cookies.get('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response Interceptor: Handle 401 (Unauthorized)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // If token expired, clear it and redirect to login
      Cookies.remove('access_token');
      Cookies.remove('refresh_token');
      // Optional: Redirect logic here
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;

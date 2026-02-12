import { http, HttpResponse } from 'msw';

const API_BASE = 'http://localhost:8000/api/v1';

export const handlers = [
  http.get(`${API_BASE}/health`, () => {
    return HttpResponse.json({ ok: true });
  }),
];

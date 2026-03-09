import { http, HttpResponse } from 'msw';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { server } from '../mocks/server';

const API_BASE = 'http://localhost:8000/api/v1';
const originalApiUrl = process.env.NEXT_PUBLIC_API_URL;

async function loadApi() {
  vi.resetModules();
  return import('@/lib/registration-code-api');
}

const SAMPLE_CODE = {
  id: 1,
  code: null,
  codePrefix: 'REG-ABC',
  codeType: 'STUDENT' as const,
  status: 'ACTIVE' as const,
  maxUses: 5,
  timesUsed: 2,
  usesRemaining: 3,
  expiresAt: '2026-04-01T00:00:00Z',
  isActive: true,
  courseId: 10,
  courseName: 'Biology 101',
  metadata: null,
  createdByUserId: 1,
  createdAt: '2026-03-01T00:00:00Z',
  archivedAt: null,
};

describe('registration code lifecycle API', () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_URL = API_BASE;
  });

  afterEach(() => {
    if (originalApiUrl === undefined) {
      delete process.env.NEXT_PUBLIC_API_URL;
      return;
    }
    process.env.NEXT_PUBLIC_API_URL = originalApiUrl;
  });

  it('listRegistrationCodes returns paginated results', async () => {
    server.use(
      http.get(`${API_BASE}/codes`, () =>
        HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [SAMPLE_CODE],
        }),
      ),
    );

    const { listRegistrationCodes } = await loadApi();
    const response = await listRegistrationCodes();

    expect(response.count).toBe(1);
    expect(response.results).toHaveLength(1);
    expect(response.results[0].codePrefix).toBe('REG-ABC');
  });

  it('listRegistrationCodes passes filter params', async () => {
    server.use(
      http.get(`${API_BASE}/codes`, ({ request }) => {
        const url = new URL(request.url);
        const status = url.searchParams.get('status');
        const codeType = url.searchParams.get('codeType');
        const includeArchived = url.searchParams.get('includeArchived');

        if (status !== 'ACTIVE' || codeType !== 'STUDENT' || includeArchived !== 'true') {
          return HttpResponse.json({ detail: 'bad params' }, { status: 400 });
        }
        return HttpResponse.json({
          count: 1,
          next: null,
          previous: null,
          results: [SAMPLE_CODE],
        });
      }),
    );

    const { listRegistrationCodes } = await loadApi();
    const response = await listRegistrationCodes({
      status: 'ACTIVE',
      codeType: 'STUDENT',
      includeArchived: true,
    });

    expect(response.count).toBe(1);
  });

  it('getRegistrationCode returns single code', async () => {
    server.use(
      http.get(`${API_BASE}/codes/1`, () => HttpResponse.json(SAMPLE_CODE)),
    );

    const { getRegistrationCode } = await loadApi();
    const code = await getRegistrationCode(1);

    expect(code.id).toBe(1);
    expect(code.codePrefix).toBe('REG-ABC');
    expect(code.status).toBe('ACTIVE');
  });

  it('updateRegistrationCodeStatus REVOKED returns updated code', async () => {
    server.use(
      http.patch(`${API_BASE}/codes/1`, async ({ request }) => {
        const body = (await request.json()) as { status?: string };
        if (body.status !== 'REVOKED') {
          return HttpResponse.json({ detail: 'bad status' }, { status: 400 });
        }
        return HttpResponse.json({ ...SAMPLE_CODE, status: 'REVOKED', isActive: false });
      }),
    );

    const { updateRegistrationCodeStatus } = await loadApi();
    const updated = await updateRegistrationCodeStatus(1, 'REVOKED');

    expect(updated.status).toBe('REVOKED');
    expect(updated.isActive).toBe(false);
  });

  it('updateRegistrationCodeStatus ARCHIVED returns updated code', async () => {
    server.use(
      http.patch(`${API_BASE}/codes/1`, async ({ request }) => {
        const body = (await request.json()) as { status?: string };
        if (body.status !== 'ARCHIVED') {
          return HttpResponse.json({ detail: 'bad status' }, { status: 400 });
        }
        return HttpResponse.json({
          ...SAMPLE_CODE,
          status: 'ARCHIVED',
          isActive: false,
          archivedAt: '2026-03-15T00:00:00Z',
        });
      }),
    );

    const { updateRegistrationCodeStatus } = await loadApi();
    const updated = await updateRegistrationCodeStatus(1, 'ARCHIVED');

    expect(updated.status).toBe('ARCHIVED');
    expect(updated.archivedAt).toBe('2026-03-15T00:00:00Z');
  });

  it('propagates 409 error for invalid status transition', async () => {
    server.use(
      http.patch(`${API_BASE}/codes/1`, () =>
        HttpResponse.json(
          { detail: 'Only ACTIVE codes can be revoked.' },
          { status: 409 },
        ),
      ),
    );

    const { updateRegistrationCodeStatus } = await loadApi();
    await expect(updateRegistrationCodeStatus(1, 'REVOKED')).rejects.toThrow();
  });
});

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockPost = vi.fn();
const mockCookieRemove = vi.fn();

async function loadLogout() {
  vi.resetModules();

  vi.doMock('@/lib/api', () => ({
    default: { post: mockPost },
  }));

  vi.doMock('js-cookie', () => ({
    default: { remove: mockCookieRemove },
  }));

  return import('@/lib/logout');
}

describe('logout', () => {
  let originalLocation: Location;

  beforeEach(() => {
    vi.clearAllMocks();
    originalLocation = window.location;

    // Mock window.location.href setter
    Object.defineProperty(window, 'location', {
      writable: true,
      value: { ...originalLocation, href: originalLocation.href },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      writable: true,
      value: originalLocation,
    });
  });

  it('calls session revocation endpoint, removes cookie, and redirects to /login', async () => {
    mockPost.mockResolvedValueOnce({});

    const { logout } = await loadLogout();
    await logout();

    expect(mockPost).toHaveBeenCalledWith('/auth/session-revocations', {});
    expect(mockCookieRemove).toHaveBeenCalledWith('user_name');
    expect(window.location.href).toBe('/login');
  });

  it('still removes cookie and redirects when revocation call fails', async () => {
    mockPost.mockRejectedValueOnce(new Error('Network error'));

    const { logout } = await loadLogout();
    await logout();

    expect(mockPost).toHaveBeenCalledWith('/auth/session-revocations', {});
    expect(mockCookieRemove).toHaveBeenCalledWith('user_name');
    expect(window.location.href).toBe('/login');
  });
});

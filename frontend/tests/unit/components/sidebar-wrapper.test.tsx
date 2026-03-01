import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { NavGroup } from '@/components/layout/sidebarWrapper';

function findLinks(groups: NavGroup[]): Array<{ label: string; href: string }> {
  return groups.flatMap((g) => g.links.map(({ label, href }) => ({ label, href })));
}

describe('Sidebar navigation configuration', () => {
  it('TEACHER nav includes Registration Codes under Courses', async () => {
    vi.resetModules();

    let capturedGroups: NavGroup[] = [];
    let capturedRole = '';

    vi.doMock('@/lib/auth-session', () => ({
      getSessionProfile: vi.fn().mockResolvedValue({
        role: 'TEACHER',
        firstName: 'Test',
        lastName: 'User',
        username: 'testuser',
      }),
      getSudoCapabilities: vi.fn().mockResolvedValue({
        hasSudo: false,
        canGrantSudo: false,
        permissions: [],
        isStaff: false,
      }),
    }));

    vi.doMock('next/navigation', () => ({
      redirect: vi.fn(),
      usePathname: vi.fn().mockReturnValue('/dashboard'),
    }));

    vi.doMock('@/components/layout/sidebar', () => ({
      Sidebar: ({ role, groups }: { role: string; groups: NavGroup[] }) => {
        capturedRole = role;
        capturedGroups = groups;
        return null;
      },
    }));

    const { SidebarWrapper } = await import('@/components/layout/sidebarWrapper');
    const element = await SidebarWrapper();
    render(element);

    expect(capturedRole).toBe('TEACHER');
    const links = findLinks(capturedGroups);
    const regCodeLink = links.find((l) => l.label === 'Registration Codes');
    expect(regCodeLink).toBeDefined();
    expect(regCodeLink!.href).toBe('/dashboard/codes');

    const myCoursesIndex = links.findIndex((l) => l.label === 'My Courses');
    const regCodeIndex = links.findIndex((l) => l.label === 'Registration Codes');
    expect(regCodeIndex).toBeGreaterThan(myCoursesIndex);
  });

  it('RESEARCHER nav includes Registration Codes', async () => {
    vi.resetModules();

    let capturedGroups: NavGroup[] = [];

    vi.doMock('@/lib/auth-session', () => ({
      getSessionProfile: vi.fn().mockResolvedValue({
        role: 'RESEARCHER',
        firstName: 'Test',
        lastName: 'Researcher',
        username: 'researcher',
      }),
      getSudoCapabilities: vi.fn().mockResolvedValue({
        hasSudo: true,
        canGrantSudo: true,
        permissions: ['CREATE_TEACHER'],
        isStaff: false,
      }),
    }));

    vi.doMock('next/navigation', () => ({
      redirect: vi.fn(),
      usePathname: vi.fn().mockReturnValue('/dashboard'),
    }));

    vi.doMock('@/components/layout/sidebar', () => ({
      Sidebar: ({ groups }: { role: string; groups: NavGroup[] }) => {
        capturedGroups = groups;
        return null;
      },
    }));

    const { SidebarWrapper } = await import('@/components/layout/sidebarWrapper');
    const element = await SidebarWrapper();
    render(element);

    const links = findLinks(capturedGroups);
    const regCodeLink = links.find((l) => l.label === 'Registration Codes');
    expect(regCodeLink).toBeDefined();
    expect(regCodeLink!.href).toBe('/dashboard/codes');
    const sudoLink = links.find((l) => l.label === 'Sudo Delegation');
    expect(sudoLink).toBeDefined();
    expect(sudoLink!.href).toBe('/dashboard/sudo');
  });

  it('STUDENT nav does NOT include Registration Codes', async () => {
    vi.resetModules();

    let capturedGroups: NavGroup[] = [];

    vi.doMock('@/lib/auth-session', () => ({
      getSessionProfile: vi.fn().mockResolvedValue({
        role: 'STUDENT',
        firstName: 'Test',
        lastName: 'Student',
        username: 'student',
      }),
      getSudoCapabilities: vi.fn().mockResolvedValue({
        hasSudo: false,
        canGrantSudo: false,
        permissions: [],
        isStaff: false,
      }),
    }));

    vi.doMock('next/navigation', () => ({
      redirect: vi.fn(),
      usePathname: vi.fn().mockReturnValue('/dashboard'),
    }));

    vi.doMock('@/components/layout/sidebar', () => ({
      Sidebar: ({ groups }: { role: string; groups: NavGroup[] }) => {
        capturedGroups = groups;
        return null;
      },
    }));

    const { SidebarWrapper } = await import('@/components/layout/sidebarWrapper');
    const element = await SidebarWrapper();
    render(element);

    const links = findLinks(capturedGroups);
    const regCodeLink = links.find((l) => l.label === 'Registration Codes');
    expect(regCodeLink).toBeUndefined();
  });

  it('redirects to /login when no profile', async () => {
    vi.resetModules();

    // In Next.js, redirect() throws a special error to halt execution.
    // We simulate that by having our mock throw.
    const redirectError = new Error('NEXT_REDIRECT');
    const mockRedirect = vi.fn().mockImplementation(() => {
      throw redirectError;
    });

    vi.doMock('@/lib/auth-session', () => ({
      getSessionProfile: vi.fn().mockResolvedValue(null),
      getSudoCapabilities: vi.fn().mockResolvedValue(null),
    }));

    vi.doMock('next/navigation', () => ({
      redirect: mockRedirect,
      usePathname: vi.fn().mockReturnValue('/dashboard'),
    }));

    vi.doMock('@/components/layout/sidebar', () => ({
      Sidebar: () => null,
    }));

    const { SidebarWrapper } = await import('@/components/layout/sidebarWrapper');
    await expect(SidebarWrapper()).rejects.toThrow('NEXT_REDIRECT');

    expect(mockRedirect).toHaveBeenCalledWith('/login');
  });

  it('RESEARCHER nav hides Sudo Delegation without canGrantSudo', async () => {
    vi.resetModules();

    let capturedGroups: NavGroup[] = [];

    vi.doMock('@/lib/auth-session', () => ({
      getSessionProfile: vi.fn().mockResolvedValue({
        role: 'RESEARCHER',
        firstName: 'Test',
        lastName: 'Researcher',
        username: 'researcher',
      }),
      getSudoCapabilities: vi.fn().mockResolvedValue({
        hasSudo: true,
        canGrantSudo: false,
        permissions: ['CREATE_TEACHER'],
        isStaff: false,
      }),
    }));

    vi.doMock('next/navigation', () => ({
      redirect: vi.fn(),
      usePathname: vi.fn().mockReturnValue('/dashboard'),
    }));

    vi.doMock('@/components/layout/sidebar', () => ({
      Sidebar: ({ groups }: { role: string; groups: NavGroup[] }) => {
        capturedGroups = groups;
        return null;
      },
    }));

    const { SidebarWrapper } = await import('@/components/layout/sidebarWrapper');
    const element = await SidebarWrapper();
    render(element);

    const links = findLinks(capturedGroups);
    const sudoLink = links.find((l) => l.label === 'Sudo Delegation');
    expect(sudoLink).toBeUndefined();
  });
});

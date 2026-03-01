import { render } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { NavItem } from '@/components/layout/sidebarWrapper';

function findLinks(items: NavItem[]): Array<{ label: string; href: string }> {
  return items
    .filter((item): item is Extract<NavItem, { type: 'link' }> => item.type === 'link')
    .map(({ label, href }) => ({ label, href }));
}

describe('Sidebar navigation configuration', () => {
  it('TEACHER nav includes Registration Codes under Courses', async () => {
    vi.resetModules();

    let capturedItems: NavItem[] = [];
    let capturedRole = '';

    vi.doMock('@/lib/auth-session', () => ({
      getSessionProfile: vi.fn().mockResolvedValue({
        role: 'TEACHER',
        firstName: 'Test',
        lastName: 'User',
        username: 'testuser',
      }),
    }));

    vi.doMock('next/navigation', () => ({
      redirect: vi.fn(),
      usePathname: vi.fn().mockReturnValue('/dashboard'),
    }));

    vi.doMock('@/components/layout/sidebar', () => ({
      Sidebar: ({ role, items }: { role: string; items: NavItem[] }) => {
        capturedRole = role;
        capturedItems = items;
        return null;
      },
    }));

    const { SidebarWrapper } = await import('@/components/layout/sidebarWrapper');
    const element = await SidebarWrapper();
    render(element);

    expect(capturedRole).toBe('TEACHER');
    const links = findLinks(capturedItems);
    const regCodeLink = links.find((l) => l.label === 'Registration Codes');
    expect(regCodeLink).toBeDefined();
    expect(regCodeLink!.href).toBe('/dashboard/codes');

    const myCoursesIndex = links.findIndex((l) => l.label === 'My Courses');
    const regCodeIndex = links.findIndex((l) => l.label === 'Registration Codes');
    expect(regCodeIndex).toBeGreaterThan(myCoursesIndex);
  });

  it('RESEARCHER nav includes Registration Codes', async () => {
    vi.resetModules();

    let capturedItems: NavItem[] = [];

    vi.doMock('@/lib/auth-session', () => ({
      getSessionProfile: vi.fn().mockResolvedValue({
        role: 'RESEARCHER',
        firstName: 'Test',
        lastName: 'Researcher',
        username: 'researcher',
      }),
    }));

    vi.doMock('next/navigation', () => ({
      redirect: vi.fn(),
      usePathname: vi.fn().mockReturnValue('/dashboard'),
    }));

    vi.doMock('@/components/layout/sidebar', () => ({
      Sidebar: ({ items }: { role: string; items: NavItem[] }) => {
        capturedItems = items;
        return null;
      },
    }));

    const { SidebarWrapper } = await import('@/components/layout/sidebarWrapper');
    const element = await SidebarWrapper();
    render(element);

    const links = findLinks(capturedItems);
    const regCodeLink = links.find((l) => l.label === 'Registration Codes');
    expect(regCodeLink).toBeDefined();
    expect(regCodeLink!.href).toBe('/dashboard/codes');
  });

  it('STUDENT nav does NOT include Registration Codes', async () => {
    vi.resetModules();

    let capturedItems: NavItem[] = [];

    vi.doMock('@/lib/auth-session', () => ({
      getSessionProfile: vi.fn().mockResolvedValue({
        role: 'STUDENT',
        firstName: 'Test',
        lastName: 'Student',
        username: 'student',
      }),
    }));

    vi.doMock('next/navigation', () => ({
      redirect: vi.fn(),
      usePathname: vi.fn().mockReturnValue('/dashboard'),
    }));

    vi.doMock('@/components/layout/sidebar', () => ({
      Sidebar: ({ items }: { role: string; items: NavItem[] }) => {
        capturedItems = items;
        return null;
      },
    }));

    const { SidebarWrapper } = await import('@/components/layout/sidebarWrapper');
    const element = await SidebarWrapper();
    render(element);

    const links = findLinks(capturedItems);
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
});

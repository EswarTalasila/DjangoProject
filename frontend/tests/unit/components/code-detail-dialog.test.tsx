import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { RegistrationCode } from '@/lib/registration-code-api';

async function loadDialog() {
  vi.resetModules();
  const mod = await import('@/components/codes/CodeDetailDialog');
  return mod.CodeDetailDialog;
}

function makeCode(overrides: Partial<RegistrationCode> = {}): RegistrationCode {
  return {
    id: 1,
    code: null,
    codePrefix: 'REG-ABC',
    codeType: 'STUDENT',
    status: 'ACTIVE',
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
    ...overrides,
  };
}

describe('CodeDetailDialog', () => {
  let onRevoke: ReturnType<typeof vi.fn<(code: RegistrationCode) => Promise<void>>>;
  let onDelete: ReturnType<typeof vi.fn<(code: RegistrationCode) => Promise<void>>>;
  let onOpenChange: ReturnType<typeof vi.fn<(open: boolean) => void>>;

  beforeEach(() => {
    vi.clearAllMocks();
    onRevoke = vi.fn<(code: RegistrationCode) => Promise<void>>().mockResolvedValue(undefined);
    onDelete = vi.fn<(code: RegistrationCode) => Promise<void>>().mockResolvedValue(undefined);
    onOpenChange = vi.fn<(open: boolean) => void>();
  });

  it('renders nothing when code is null', async () => {
    const Dialog = await loadDialog();
    const { container } = render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={null}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(container.innerHTML).toBe('');
  });

  it('shows all code details for an ACTIVE code', async () => {
    const Dialog = await loadDialog();
    const code = makeCode();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={code}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.getByText('Code Details')).toBeInTheDocument();
    expect(screen.getByText('REG-ABC')).toBeInTheDocument();
    expect(screen.getByText('Student')).toBeInTheDocument();
    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
    expect(screen.getByText(/3 remaining/)).toBeInTheDocument();
    expect(screen.getByText('Biology 101')).toBeInTheDocument();
    expect(screen.getByText('User #1')).toBeInTheDocument();
  });

  it('shows Revoke and Delete buttons for ACTIVE code', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ status: 'ACTIVE' })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.getByRole('button', { name: /Revoke/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Delete/i })).toBeInTheDocument();
  });

  it('shows Delete button for EXHAUSTED code, no Revoke', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ status: 'EXHAUSTED' })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.getByRole('button', { name: /Delete/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Revoke/i })).not.toBeInTheDocument();
  });

  it('shows Delete button for EXPIRED code', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ status: 'EXPIRED' })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.getByRole('button', { name: /Delete/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Revoke/i })).not.toBeInTheDocument();
  });

  it('shows Delete button for REVOKED code', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ status: 'REVOKED' })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.getByRole('button', { name: /Delete/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Revoke/i })).not.toBeInTheDocument();
  });

  it('shows Delete button for ARCHIVED code and no Revoke', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ status: 'ARCHIVED', archivedAt: '2026-03-15T00:00:00Z' })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.queryByRole('button', { name: /Revoke/i })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Delete/i })).toBeInTheDocument();
  });

  it('shows archived date when present', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ status: 'ARCHIVED', archivedAt: '2026-03-15T00:00:00Z' })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.getByText('Archived')).toBeInTheDocument();
  });

  it('revoke button calls onRevoke with the code', async () => {
    const Dialog = await loadDialog();
    const code = makeCode({ status: 'ACTIVE' });
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={code}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Revoke/i }));

    expect(onRevoke).toHaveBeenCalledWith(code);
  });

  it('delete button calls onDelete with the code', async () => {
    const Dialog = await loadDialog();
    const code = makeCode({ status: 'EXHAUSTED' });
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={code}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: /Delete/i }));

    expect(onDelete).toHaveBeenCalledWith(code);
  });

  it('disables action buttons when isActionLoading is true', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ status: 'ACTIVE' })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={true}
      />,
    );

    expect(screen.getByRole('button', { name: /Revoke/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /Delete/i })).toBeDisabled();
  });

  it('renders metadata key-value pairs', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ metadata: { cohort: 'Spring2026', section: 'A' } })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.getByText('Metadata')).toBeInTheDocument();
    expect(screen.getByText('cohort:')).toBeInTheDocument();
    expect(screen.getByText('Spring2026')).toBeInTheDocument();
    expect(screen.getByText('section:')).toBeInTheDocument();
    expect(screen.getByText('A')).toBeInTheDocument();
  });

  it('does not render metadata section when metadata is null', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ metadata: null })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.queryByText('Metadata')).not.toBeInTheDocument();
  });

  it('does not render metadata section when metadata is empty object', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ metadata: {} })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    expect(screen.queryByText('Metadata')).not.toBeInTheDocument();
  });

  it('shows dash for course when courseName is null', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={makeCode({ courseId: null, courseName: null })}
        onRevoke={onRevoke}
        onDelete={onDelete}
        isActionLoading={false}
      />,
    );

    // The Course field should show a dash
    const courseLabel = screen.getByText('Course');
    const courseValue = courseLabel.parentElement?.querySelector('p:last-child');
    expect(courseValue?.textContent).toBe('-');
  });
});

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { SudoGrantListItem } from '@/lib/sudo-api';

const MOCK_GRANT: SudoGrantListItem = {
  id: 1,
  user: { id: 10, username: 'researcher1', name: 'Alice Researcher' },
  permissions: ['CREATE_TEACHER', 'EDIT_USER'],
  canGrantSudo: false,
  grantedAt: '2026-01-15T10:00:00Z',
};

async function loadRevokeSudoDialog() {
  const imported = await import('@/components/sudo/RevokeSudoDialog');
  return imported.default;
}

describe('RevokeSudoDialog', () => {
  it('shows researcher name and permission count', async () => {
    const RevokeSudoDialog = await loadRevokeSudoDialog();
    render(
      <RevokeSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        grant={MOCK_GRANT}
        isLoading={false}
        onConfirm={vi.fn()}
      />,
    );

    expect(screen.getByText('Revoke Sudo Grant')).toBeInTheDocument();
    expect(screen.getByText(/Alice Researcher/)).toBeInTheDocument();
    expect(screen.getByText(/2 sudo permissions/)).toBeInTheDocument();
  });

  it('calls onConfirm when Revoke is clicked', async () => {
    const onConfirm = vi.fn();
    const RevokeSudoDialog = await loadRevokeSudoDialog();
    render(
      <RevokeSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        grant={MOCK_GRANT}
        isLoading={false}
        onConfirm={onConfirm}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Confirm revoke sudo' }));
    expect(onConfirm).toHaveBeenCalledOnce();
  });

  it('shows loading state when isLoading', async () => {
    const RevokeSudoDialog = await loadRevokeSudoDialog();
    render(
      <RevokeSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        grant={MOCK_GRANT}
        isLoading={true}
        onConfirm={vi.fn()}
      />,
    );

    expect(screen.getByText('Revoking...')).toBeInTheDocument();
  });

  it('renders nothing when grant is null', async () => {
    const RevokeSudoDialog = await loadRevokeSudoDialog();
    const { container } = render(
      <RevokeSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        grant={null}
        isLoading={false}
        onConfirm={vi.fn()}
      />,
    );

    expect(container.innerHTML).toBe('');
  });
});

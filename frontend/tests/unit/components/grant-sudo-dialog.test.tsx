import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { StaffUser } from '@/lib/password-reset-api';
import type { SudoGrantListItem } from '@/lib/sudo-api';

const STAFF_USERS: StaffUser[] = [
  { id: 10, name: 'Alice', username: 'alice@test.com', email: 'alice@test.com', role: 'RESEARCHER' },
  { id: 11, name: 'Bob', username: 'bob@test.com', email: 'bob@test.com', role: 'RESEARCHER' },
  { id: 12, name: 'Carol', username: 'carol@test.com', email: 'carol@test.com', role: 'TEACHER' },
];

const EXISTING_GRANTS: SudoGrantListItem[] = [
  {
    id: 1,
    user: { id: 10, username: 'alice@test.com', name: 'Alice' },
    permissions: ['CREATE_TEACHER'],
    canGrantSudo: false,
    grantedAt: '2026-01-15T10:00:00Z',
  },
  {
    id: 2,
    user: { id: 11, username: 'bob@test.com', name: 'Bob' },
    permissions: ['CREATE_TEACHER', 'ISSUE_RESEARCHER_REG_CODE'],
    canGrantSudo: true,
    grantedAt: '2026-01-16T10:00:00Z',
  },
];

const USER_PERMISSIONS = ['CREATE_TEACHER', 'EDIT_USER', 'ISSUE_RESEARCHER_REG_CODE'];

async function loadGrantSudoDialog() {
  const imported = await import('@/components/sudo/GrantSudoDialog');
  return imported.default;
}

describe('GrantSudoDialog', () => {
  it('shows researchers except self and non-researchers', async () => {
    const GrantSudoDialog = await loadGrantSudoDialog();
    render(
      <GrantSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        isLoading={false}
        staffUsers={STAFF_USERS}
        currentUserId={99}
        existingGrants={EXISTING_GRANTS}
        userPermissions={USER_PERMISSIONS}
        onSubmit={vi.fn()}
      />,
    );

    const select = screen.getByLabelText('Researcher');
    const options = Array.from((select as HTMLSelectElement).options);
    const optionTexts = options.map((o) => o.text);

    // Both researchers are eligible (existing grant can be updated).
    expect(optionTexts.some((t) => t.includes('Bob'))).toBe(true);
    expect(optionTexts.some((t) => t.includes('Alice'))).toBe(true);
    // Carol excluded (teacher)
    expect(optionTexts.some((t) => t.includes('Carol'))).toBe(false);
  });

  it('shows only delegable permissions (excludes ISSUE_RESEARCHER_REG_CODE)', async () => {
    const GrantSudoDialog = await loadGrantSudoDialog();
    render(
      <GrantSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        isLoading={false}
        staffUsers={STAFF_USERS}
        currentUserId={99}
        existingGrants={[]}
        userPermissions={USER_PERMISSIONS}
        onSubmit={vi.fn()}
      />,
    );

    expect(screen.getByText('User Management Permissions')).toBeInTheDocument();
    expect(screen.getByText('Create Teacher Accounts')).toBeInTheDocument();
    expect(screen.getByText('Edit User Accounts')).toBeInTheDocument();
    expect(screen.queryByText('Issue Researcher Registration Codes')).not.toBeInTheDocument();
  });

  it('calls onSubmit with correct values', async () => {
    const onSubmit = vi.fn();
    const GrantSudoDialog = await loadGrantSudoDialog();
    render(
      <GrantSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        isLoading={false}
        staffUsers={STAFF_USERS}
        currentUserId={99}
        existingGrants={[]}
        userPermissions={USER_PERMISSIONS}
        onSubmit={onSubmit}
      />,
    );

    const user = userEvent.setup();

    // Select researcher
    await user.selectOptions(screen.getByLabelText('Researcher'), '10');

    // Check a permission
    await user.click(screen.getByLabelText('Create Teacher Accounts'));

    // Submit
    await user.click(screen.getByRole('button', { name: 'Grant Sudo' }));

    expect(onSubmit).toHaveBeenCalledWith(10, expect.arrayContaining(['CREATE_TEACHER']), false);
  });

  it('preloads permissions when selecting researcher with existing grant', async () => {
    const GrantSudoDialog = await loadGrantSudoDialog();
    render(
      <GrantSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        isLoading={false}
        staffUsers={STAFF_USERS}
        currentUserId={99}
        existingGrants={EXISTING_GRANTS}
        userPermissions={USER_PERMISSIONS}
        onSubmit={vi.fn()}
      />,
    );

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText('Researcher'), '10');

    expect(screen.getByLabelText('Create Teacher Accounts')).toBeChecked();
    expect(
      screen.getByText("Existing sudo grant found. Saving will replace this researcher's permission set."),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save Sudo' })).toBeInTheDocument();
  });

  it('shows locked admin-only state for grants that include non-editable permissions', async () => {
    const GrantSudoDialog = await loadGrantSudoDialog();
    render(
      <GrantSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        isLoading={false}
        staffUsers={STAFF_USERS}
        currentUserId={99}
        existingGrants={EXISTING_GRANTS}
        userPermissions={USER_PERMISSIONS}
        onSubmit={vi.fn()}
      />,
    );

    const user = userEvent.setup();
    await user.selectOptions(screen.getByLabelText('Researcher'), '11');

    expect(screen.getByLabelText('Grant Sudo Delegation (admin-only)')).toBeChecked();
    expect(
      screen.getByText(
        'This grant includes admin-only capabilities and cannot be fully edited here. Use Django admin.',
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Save Sudo' })).toBeDisabled();
  });

  it('disables Grant Sudo button when no researcher or permissions selected', async () => {
    const GrantSudoDialog = await loadGrantSudoDialog();
    render(
      <GrantSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        isLoading={false}
        staffUsers={STAFF_USERS}
        currentUserId={99}
        existingGrants={[]}
        userPermissions={USER_PERMISSIONS}
        onSubmit={vi.fn()}
      />,
    );

    const submitButton = screen.getByRole('button', { name: 'Grant Sudo' });
    expect(submitButton).toBeDisabled();
  });

  it('resets form when dialog closes', async () => {
    const onOpenChange = vi.fn();
    const GrantSudoDialog = await loadGrantSudoDialog();
    render(
      <GrantSudoDialog
        open={true}
        onOpenChange={onOpenChange}
        isLoading={false}
        staffUsers={STAFF_USERS}
        currentUserId={99}
        existingGrants={[]}
        userPermissions={USER_PERMISSIONS}
        onSubmit={vi.fn()}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('excludes the current researcher from selectable targets', async () => {
    const GrantSudoDialog = await loadGrantSudoDialog();
    render(
      <GrantSudoDialog
        open={true}
        onOpenChange={vi.fn()}
        isLoading={false}
        staffUsers={STAFF_USERS}
        currentUserId={11}
        existingGrants={[]}
        userPermissions={USER_PERMISSIONS}
        onSubmit={vi.fn()}
      />,
    );

    const select = screen.getByLabelText('Researcher');
    const options = Array.from((select as HTMLSelectElement).options);
    const optionTexts = options.map((o) => o.text);

    expect(optionTexts.some((t) => t.includes('Bob'))).toBe(false);
  });
});

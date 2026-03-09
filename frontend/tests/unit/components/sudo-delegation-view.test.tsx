import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockListSudoGrants = vi.fn();
const mockGrantSudo = vi.fn();
const mockRevokeSudoGrant = vi.fn();
const mockGetMySudoGrant = vi.fn();
const mockListStaffUsers = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock('@/lib/sudo-api', () => ({
    listSudoGrants: mockListSudoGrants,
    grantSudo: mockGrantSudo,
    revokeSudoGrant: mockRevokeSudoGrant,
  }));
  vi.doMock('@/lib/password-reset-api', () => ({
    getMySudoGrant: mockGetMySudoGrant,
    listStaffUsers: mockListStaffUsers,
  }));
  vi.doMock('sonner', () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
}

async function loadSudoDelegationView() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import('@/components/sudo/SudoDelegationView');
  return imported.default;
}

const GRANT_1 = {
  id: 1,
  user: { id: 10, username: 'researcher1', name: 'Alice Researcher' },
  permissions: ['CREATE_TEACHER', 'EDIT_USER'],
  canGrantSudo: false,
  grantedAt: '2026-01-15T10:00:00Z',
};

const MY_GRANT = {
  hasSudo: true,
  canGrantSudo: true,
  permissions: ['CREATE_TEACHER', 'EDIT_USER', 'DELETE_USER'],
  isStaff: false,
};

const STAFF_USERS = [
  { id: 10, name: 'Alice', username: 'alice@test.com', email: 'alice@test.com', role: 'RESEARCHER' },
  { id: 20, name: 'Bob', username: 'bob@test.com', email: 'bob@test.com', role: 'RESEARCHER' },
];

describe('SudoDelegationView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders grants table', async () => {
    mockListSudoGrants.mockResolvedValueOnce([GRANT_1]);
    mockGetMySudoGrant.mockResolvedValueOnce(MY_GRANT);
    mockListStaffUsers.mockResolvedValueOnce(STAFF_USERS);

    const SudoDelegationView = await loadSudoDelegationView();
    render(<SudoDelegationView currentUserId={99} />);

    await waitFor(() => {
      expect(screen.getByText('Alice Researcher')).toBeInTheDocument();
    });

    expect(screen.getByText('Create Teacher Accounts')).toBeInTheDocument();
    expect(screen.getByText('Edit User Accounts')).toBeInTheDocument();
  });

  it('shows empty state when no grants', async () => {
    mockListSudoGrants.mockResolvedValueOnce([]);
    mockGetMySudoGrant.mockResolvedValueOnce(MY_GRANT);
    mockListStaffUsers.mockResolvedValueOnce([]);

    const SudoDelegationView = await loadSudoDelegationView();
    render(<SudoDelegationView currentUserId={99} />);

    await waitFor(() => {
      expect(screen.getByText('No sudo grants found.')).toBeInTheDocument();
    });
  });

  it('shows access-denied when canGrantSudo is false', async () => {
    mockListSudoGrants.mockResolvedValueOnce([]);
    mockGetMySudoGrant.mockResolvedValueOnce({
      ...MY_GRANT,
      canGrantSudo: false,
    });
    mockListStaffUsers.mockResolvedValueOnce([]);

    const SudoDelegationView = await loadSudoDelegationView();
    render(<SudoDelegationView currentUserId={99} />);

    await waitFor(() => {
      expect(
        screen.getByText('You do not have permission to delegate sudo access.'),
      ).toBeInTheDocument();
    });

    expect(screen.queryByRole('button', { name: /Grant Sudo/i })).not.toBeInTheDocument();
  });

  it('shows loading state', async () => {
    mockListSudoGrants.mockImplementation(() => new Promise(() => {}));
    mockGetMySudoGrant.mockImplementation(() => new Promise(() => {}));
    mockListStaffUsers.mockImplementation(() => new Promise(() => {}));

    const SudoDelegationView = await loadSudoDelegationView();
    render(<SudoDelegationView currentUserId={99} />);

    expect(screen.getByText('Loading grants...')).toBeInTheDocument();
  });

  it('shows error state on load failure', async () => {
    mockListSudoGrants.mockRejectedValueOnce(new Error('Network error'));
    mockGetMySudoGrant.mockRejectedValueOnce(new Error('Network error'));
    mockListStaffUsers.mockRejectedValueOnce(new Error('Network error'));

    const SudoDelegationView = await loadSudoDelegationView();
    render(<SudoDelegationView currentUserId={99} />);

    await waitFor(() => {
      expect(screen.getByText('Failed to load sudo grants.')).toBeInTheDocument();
    });
  });

  it('Grant Sudo button opens dialog', async () => {
    mockListSudoGrants.mockResolvedValueOnce([]);
    mockGetMySudoGrant.mockResolvedValueOnce(MY_GRANT);
    mockListStaffUsers.mockResolvedValueOnce(STAFF_USERS);

    const SudoDelegationView = await loadSudoDelegationView();
    render(<SudoDelegationView currentUserId={99} />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /Grant Sudo/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Grant Sudo/i }));

    await waitFor(() => {
      expect(screen.getByText('Grant Sudo Permissions')).toBeInTheDocument();
    });
  });

  it('Revoke button opens confirmation dialog', async () => {
    mockListSudoGrants.mockResolvedValueOnce([GRANT_1]);
    mockGetMySudoGrant.mockResolvedValueOnce(MY_GRANT);
    mockListStaffUsers.mockResolvedValueOnce(STAFF_USERS);

    const SudoDelegationView = await loadSudoDelegationView();
    render(<SudoDelegationView currentUserId={99} />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText('Alice Researcher')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Revoke/i }));

    await waitFor(() => {
      expect(screen.getByText('Revoke Sudo Grant')).toBeInTheDocument();
      // Name appears in both the table row and the dialog description
      expect(screen.getAllByText(/Alice Researcher/).length).toBeGreaterThanOrEqual(2);
    });
  });

  it('confirms revoke and refreshes data', async () => {
    mockListSudoGrants.mockResolvedValueOnce([GRANT_1]);
    mockGetMySudoGrant.mockResolvedValueOnce(MY_GRANT);
    mockListStaffUsers.mockResolvedValueOnce(STAFF_USERS);
    mockRevokeSudoGrant.mockResolvedValueOnce(undefined);
    // After revoke, reload returns empty
    mockListSudoGrants.mockResolvedValueOnce([]);
    mockGetMySudoGrant.mockResolvedValueOnce(MY_GRANT);
    mockListStaffUsers.mockResolvedValueOnce(STAFF_USERS);

    const SudoDelegationView = await loadSudoDelegationView();
    render(<SudoDelegationView currentUserId={99} />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText('Alice Researcher')).toBeInTheDocument();
    });

    // Open revoke dialog
    await user.click(screen.getByRole('button', { name: /Revoke/i }));

    await waitFor(() => {
      expect(screen.getByText('Revoke Sudo Grant')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: 'Confirm revoke sudo' }));

    await waitFor(() => {
      expect(mockRevokeSudoGrant).toHaveBeenCalledWith(1);
      expect(mockToastSuccess).toHaveBeenCalledWith('Sudo revoked for Alice Researcher.');
    });
  });
});

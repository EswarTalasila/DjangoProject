import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const mockListRegistrationCodes = vi.fn();
const mockUpdateRegistrationCodeStatus = vi.fn();
const mockCreateRegistrationCodes = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock('@/lib/registration-code-api', () => ({
    listRegistrationCodes: mockListRegistrationCodes,
    updateRegistrationCodeStatus: mockUpdateRegistrationCodeStatus,
    createRegistrationCodes: mockCreateRegistrationCodes,
  }));
  vi.doMock('sonner', () => ({
    toast: { success: mockToastSuccess, error: mockToastError },
  }));
}

async function loadCodeManagementView() {
  vi.resetModules();
  setupModuleMocks();
  const imported = await import('@/components/codes/CodeManagementView');
  return imported.default;
}

const ACTIVE_CODE = {
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

const EXHAUSTED_CODE = {
  ...ACTIVE_CODE,
  id: 2,
  codePrefix: 'REG-XYZ',
  status: 'EXHAUSTED' as const,
  timesUsed: 5,
  usesRemaining: 0,
  isActive: false,
};

describe('CodeManagementView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockListRegistrationCodes.mockReset();
    mockUpdateRegistrationCodeStatus.mockReset();
    mockCreateRegistrationCodes.mockReset();
    mockToastSuccess.mockReset();
    mockToastError.mockReset();
  });

  it('renders code table with data', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 2,
      next: null,
      previous: null,
      results: [ACTIVE_CODE, EXHAUSTED_CODE],
    });

    const CodeManagementView = await loadCodeManagementView();
    render(<CodeManagementView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText('REG-ABC')).toBeInTheDocument();
      expect(screen.getByText('REG-XYZ')).toBeInTheDocument();
    });

    expect(screen.getByText('ACTIVE')).toBeInTheDocument();
    expect(screen.getByText('EXHAUSTED')).toBeInTheDocument();
    expect(screen.getByText('2/5')).toBeInTheDocument();
    expect(screen.getAllByText('Biology 101').length).toBeGreaterThanOrEqual(1);
  });

  it('renders empty state when no codes', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });

    const CodeManagementView = await loadCodeManagementView();
    render(<CodeManagementView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText('No registration codes found.')).toBeInTheDocument();
    });
  });

  it('filters by status', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 2,
      next: null,
      previous: null,
      results: [ACTIVE_CODE, EXHAUSTED_CODE],
    });
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [ACTIVE_CODE],
    });

    const CodeManagementView = await loadCodeManagementView();
    render(<CodeManagementView userRole="TEACHER" />);

    await waitFor(() => {
      expect(screen.getByText('REG-ABC')).toBeInTheDocument();
    });

    const user = userEvent.setup();
    const statusSelect = screen.getByLabelText('Status');
    await user.selectOptions(statusSelect, 'ACTIVE');

    await waitFor(() => {
      expect(mockListRegistrationCodes).toHaveBeenCalledTimes(2);
      expect(mockListRegistrationCodes).toHaveBeenLastCalledWith({
        status: 'ACTIVE',
        codeType: undefined,
        includeArchived: false,
      });
    });
  });

  it('revoke action calls API and refreshes', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [ACTIVE_CODE],
    });
    mockUpdateRegistrationCodeStatus.mockResolvedValueOnce({
      ...ACTIVE_CODE,
      status: 'REVOKED',
    });
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [{ ...ACTIVE_CODE, status: 'REVOKED' }],
    });

    const CodeManagementView = await loadCodeManagementView();
    render(<CodeManagementView userRole="TEACHER" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText('REG-ABC')).toBeInTheDocument();
    });

    const row = screen.getByText('REG-ABC').closest('tr')!;
    const menuButton = within(row).getByRole('button');
    await user.click(menuButton);

    const revokeItem = await screen.findByText('Revoke');
    await user.click(revokeItem);

    await waitFor(() => {
      expect(mockUpdateRegistrationCodeStatus).toHaveBeenCalledWith(1, 'REVOKED');
      expect(mockToastSuccess).toHaveBeenCalledWith('Code REG-ABC revoked.');
    });
  });

  it('archive action calls API and refreshes', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [EXHAUSTED_CODE],
    });
    mockUpdateRegistrationCodeStatus.mockResolvedValueOnce({
      ...EXHAUSTED_CODE,
      status: 'ARCHIVED',
    });
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });

    const CodeManagementView = await loadCodeManagementView();
    render(<CodeManagementView userRole="TEACHER" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText('REG-XYZ')).toBeInTheDocument();
    });

    const row = screen.getByText('REG-XYZ').closest('tr')!;
    const menuButton = within(row).getByRole('button');
    await user.click(menuButton);

    const archiveItem = await screen.findByText('Archive');
    await user.click(archiveItem);

    await waitFor(() => {
      expect(mockUpdateRegistrationCodeStatus).toHaveBeenCalledWith(2, 'ARCHIVED');
      expect(mockToastSuccess).toHaveBeenCalledWith('Code REG-XYZ archived.');
    });
  });

  it('detail dialog opens with correct data', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [ACTIVE_CODE],
    });

    const CodeManagementView = await loadCodeManagementView();
    render(<CodeManagementView userRole="TEACHER" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText('REG-ABC')).toBeInTheDocument();
    });

    const row = screen.getByText('REG-ABC').closest('tr')!;
    const menuButton = within(row).getByRole('button');
    await user.click(menuButton);

    const viewDetails = await screen.findByText('View Details');
    await user.click(viewDetails);

    await waitFor(() => {
      expect(screen.getByText('Code Details')).toBeInTheDocument();
      expect(screen.getByText('3 remaining', { exact: false })).toBeInTheDocument();
    });
  });

  it('"Generate Code" button opens create dialog', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });

    const CodeManagementView = await loadCodeManagementView();
    render(<CodeManagementView userRole="TEACHER" />);

    const user = userEvent.setup();
    await waitFor(() => {
      expect(screen.getByText('No registration codes found.')).toBeInTheDocument();
    });

    await user.click(screen.getByRole('button', { name: /Generate Code/i }));

    await waitFor(() => {
      expect(screen.getByText('Generate registration code')).toBeInTheDocument();
    });
  });
});

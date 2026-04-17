import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockListRegistrationCodes = vi.fn();
const mockUpdateRegistrationCodeStatus = vi.fn();
const mockDeleteRegistrationCode = vi.fn();
const mockCreateRegistrationCodes = vi.fn();
const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();

function setupModuleMocks() {
  vi.doMock('@/lib/registration-code-api', () => ({
    listRegistrationCodes: mockListRegistrationCodes,
    updateRegistrationCodeStatus: mockUpdateRegistrationCodeStatus,
    deleteRegistrationCode: mockDeleteRegistrationCode,
    createRegistrationCodes: mockCreateRegistrationCodes,
  }));
  vi.doMock('@/lib/course-api', () => ({
    listCourses: vi.fn().mockResolvedValue([
      { id: 1, name: 'Test Course', studentCount: 0, assignmentIds: [] },
    ]),
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

function getDesktopRow(prefix: string): HTMLTableRowElement {
  const match = screen
    .getAllByText(prefix)
    .find((node) => node.closest('tr') instanceof HTMLTableRowElement);
  if (!match) {
    throw new Error(`No desktop table row found for code ${prefix}.`);
  }
  return match.closest('tr') as HTMLTableRowElement;
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
    vi.stubGlobal('confirm', vi.fn(() => true));
    mockListRegistrationCodes.mockReset();
    mockUpdateRegistrationCodeStatus.mockReset();
    mockDeleteRegistrationCode.mockReset();
    mockCreateRegistrationCodes.mockReset();
    mockToastSuccess.mockReset();
    mockToastError.mockReset();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
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
      expect(screen.getAllByText('REG-ABC').length).toBeGreaterThan(0);
      expect(screen.getAllByText('REG-XYZ').length).toBeGreaterThan(0);
    });

    expect(screen.getAllByText('ACTIVE').length).toBeGreaterThan(0);
    expect(screen.getAllByText('EXHAUSTED').length).toBeGreaterThan(0);
    expect(screen.getAllByText('2/5').length).toBeGreaterThan(0);
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
      expect(screen.getAllByText('REG-ABC').length).toBeGreaterThan(0);
    });

    const user = userEvent.setup();
    const activeChip = screen.getByRole('button', { name: 'Active' });
    await user.click(activeChip);

    await waitFor(() => {
      expect(mockListRegistrationCodes).toHaveBeenCalledTimes(2);
      expect(mockListRegistrationCodes).toHaveBeenLastCalledWith({
        status: 'ACTIVE',
        codeType: 'STUDENT',
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
      expect(screen.getAllByText('REG-ABC').length).toBeGreaterThan(0);
    });

    const row = getDesktopRow('REG-ABC');
    const menuButton = within(row).getByRole('button');
    await user.click(menuButton);

    const revokeItem = await screen.findByText('Revoke');
    await user.click(revokeItem);

    await waitFor(() => {
      expect(mockUpdateRegistrationCodeStatus).toHaveBeenCalledWith(1, 'REVOKED');
      expect(mockToastSuccess).toHaveBeenCalledWith('Code REG-ABC revoked.');
    });
  });

  it('delete action calls API and refreshes', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 1,
      next: null,
      previous: null,
      results: [EXHAUSTED_CODE],
    });
    mockDeleteRegistrationCode.mockResolvedValueOnce(undefined);
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
      expect(screen.getAllByText('REG-XYZ').length).toBeGreaterThan(0);
    });

    const row = getDesktopRow('REG-XYZ');
    const menuButton = within(row).getByRole('button');
    await user.click(menuButton);

    const deleteItem = await screen.findByText('Delete');
    await user.click(deleteItem);

    await waitFor(() => {
      expect(mockDeleteRegistrationCode).toHaveBeenCalledWith(2);
      expect(mockToastSuccess).toHaveBeenCalledWith('Code REG-XYZ deleted.');
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
      expect(screen.getAllByText('REG-ABC').length).toBeGreaterThan(0);
    });

    const row = getDesktopRow('REG-ABC');
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

  it('researcher without ISSUE_STUDENT_REG_CODE sees only Teacher tab', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });

    const CodeManagementView = await loadCodeManagementView();
    render(
      <CodeManagementView userRole="RESEARCHER" researcherPermissions={[]} isStaff={false} />,
    );

    await waitFor(() => {
      expect(screen.getByText('No registration codes found.')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: 'Teacher' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Student' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Researcher' })).not.toBeInTheDocument();
  });

  it('researcher with ISSUE_STUDENT_REG_CODE sees Student and Teacher tabs', async () => {
    mockListRegistrationCodes.mockResolvedValueOnce({
      count: 0,
      next: null,
      previous: null,
      results: [],
    });

    const CodeManagementView = await loadCodeManagementView();
    render(
      <CodeManagementView
        userRole="RESEARCHER"
        researcherPermissions={['ISSUE_STUDENT_REG_CODE']}
        isStaff={false}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText('No registration codes found.')).toBeInTheDocument();
    });

    expect(screen.getByRole('button', { name: 'Student' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Teacher' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Researcher' })).not.toBeInTheDocument();
  });
});

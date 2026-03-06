import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/course-api', () => ({
  listCourses: vi.fn().mockResolvedValue([
    { id: 1, name: 'Intro to CS', studentCount: 10, assignmentIds: [] },
    { id: 2, name: 'Data Structures', studentCount: 5, assignmentIds: [] },
  ]),
}));

type CreateCodeDialogValues = {
  codeType: 'STUDENT' | 'TEACHER' | 'RESEARCHER';
  count: number;
  usesPerCode: number;
  expiresAt: string;
  courseId?: number;
};

async function loadDialog() {
  vi.resetModules();
  const mod = await import('@/components/codes/CreateRegistrationCodeDialog');
  return mod.CreateRegistrationCodeDialog;
}

describe('CreateRegistrationCodeDialog', () => {
  let onSubmit: ReturnType<typeof vi.fn<(values: CreateCodeDialogValues) => Promise<void>>>;
  let onOpenChange: ReturnType<typeof vi.fn<(open: boolean) => void>>;

  beforeEach(() => {
    vi.clearAllMocks();
    onSubmit = vi.fn<(values: CreateCodeDialogValues) => Promise<void>>().mockResolvedValue(undefined);
    onOpenChange = vi.fn<(open: boolean) => void>();
  });

  it('renders all form fields including count', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test Title"
        description="Test description"
        allowedCodeTypes={['STUDENT', 'TEACHER']}
        initialCodeType="STUDENT"
        onSubmit={onSubmit}
      />,
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Code type')).toBeInTheDocument();
      expect(screen.getByLabelText('Number of codes')).toBeInTheDocument();
      expect(screen.getByLabelText('Uses per code')).toBeInTheDocument();
      expect(screen.getByLabelText('Expires at')).toBeInTheDocument();
    });
  });

  it('always shows code type selector even with single type', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        lockCodeType
        onSubmit={onSubmit}
      />,
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Code type')).toBeInTheDocument();
      expect(screen.getByLabelText('Code type')).toBeDisabled();
      expect(screen.getByLabelText('Number of codes')).toBeInTheDocument();
    });
  });

  it('submits with correct payload including count and courseId', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        lockCodeType
        onSubmit={onSubmit}
      />,
    );

    const user = userEvent.setup();

    // Wait for courses to load and select one
    await waitFor(() => {
      expect(screen.getByLabelText('Course')).toBeInTheDocument();
    });
    await user.selectOptions(screen.getByLabelText('Course'), '1');

    // Change count to 3
    const countInput = screen.getByLabelText('Number of codes');
    await user.clear(countInput);
    await user.type(countInput, '3');

    // Change uses per code to 5
    const usesInput = screen.getByLabelText('Uses per code');
    await user.clear(usesInput);
    await user.type(usesInput, '5');

    await user.click(screen.getByRole('button', { name: 'Create code' }));

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });

    const submitted = onSubmit.mock.calls[0][0];
    expect(submitted.codeType).toBe('STUDENT');
    expect(submitted.count).toBe(3);
    expect(submitted.usesPerCode).toBe(5);
    expect(submitted.courseId).toBe(1);
    expect(submitted.expiresAt).toBeTruthy();
  });

  it('shows count validation error when count < 1', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['TEACHER']}
        initialCodeType="TEACHER"
        lockCodeType
        onSubmit={onSubmit}
      />,
    );

    const user = userEvent.setup();
    const countInput = screen.getByLabelText('Number of codes');
    await user.clear(countInput);
    await user.type(countInput, '0');

    await user.click(screen.getByRole('button', { name: 'Create code' }));

    await waitFor(() => {
      expect(screen.getByText('Number of codes must be at least 1.')).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('shows uses validation error when usesPerCode < 1', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['TEACHER']}
        initialCodeType="TEACHER"
        lockCodeType
        onSubmit={onSubmit}
      />,
    );

    const user = userEvent.setup();
    const usesInput = screen.getByLabelText('Uses per code');
    await user.clear(usesInput);
    await user.type(usesInput, '0');

    await user.click(screen.getByRole('button', { name: 'Create code' }));

    await waitFor(() => {
      expect(screen.getByText('Uses per code must be at least 1.')).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('shows expiration validation error for past date', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['TEACHER']}
        initialCodeType="TEACHER"
        lockCodeType
        onSubmit={onSubmit}
      />,
    );

    const user = userEvent.setup();
    const expiresInput = screen.getByLabelText('Expires at');
    // Set to a date in the past
    await user.clear(expiresInput);
    await user.type(expiresInput, '2020-01-01T00:00');

    await user.click(screen.getByRole('button', { name: 'Create code' }));

    await waitFor(() => {
      expect(screen.getByText('Expiration must be in the future.')).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('cancel button calls onOpenChange(false)', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['TEACHER']}
        initialCodeType="TEACHER"
        onSubmit={onSubmit}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('renders code type selector with all allowed types', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['TEACHER', 'RESEARCHER']}
        initialCodeType="TEACHER"
        onSubmit={onSubmit}
      />,
    );

    const select = screen.getByLabelText('Code type');
    expect(select).toBeInTheDocument();
    expect(screen.getByText('Teacher')).toBeInTheDocument();
    expect(screen.getByText('Researcher')).toBeInTheDocument();
  });

  it('disables inputs when isLoading is true', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        isLoading={true}
        title="Test"
        description="Desc"
        allowedCodeTypes={['TEACHER']}
        initialCodeType="TEACHER"
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByLabelText('Number of codes')).toBeDisabled();
    expect(screen.getByLabelText('Uses per code')).toBeDisabled();
    expect(screen.getByLabelText('Expires at')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Create code' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
  });

  it('locks code type selector when lockCodeType is true', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['TEACHER']}
        initialCodeType="TEACHER"
        lockCodeType
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByLabelText('Code type')).toBeDisabled();
    expect(screen.getByText('Your permissions only allow this code type.')).toBeInTheDocument();
  });

  it('shows course picker when STUDENT code type is selected', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['STUDENT', 'TEACHER']}
        initialCodeType="STUDENT"
        onSubmit={onSubmit}
      />,
    );

    await waitFor(() => {
      expect(screen.getByLabelText('Course')).toBeInTheDocument();
    });
    expect(screen.getByText('Intro to CS')).toBeInTheDocument();
    expect(screen.getByText('Data Structures')).toBeInTheDocument();
  });

  it('hides course picker for non-STUDENT code types', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['TEACHER', 'RESEARCHER']}
        initialCodeType="TEACHER"
        onSubmit={onSubmit}
      />,
    );

    expect(screen.queryByLabelText('Course')).not.toBeInTheDocument();
  });

  it('validates course selection required for student codes', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        lockCodeType
        onSubmit={onSubmit}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Create code' }));

    await waitFor(() => {
      expect(screen.getByText('Please select a course for student codes.')).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });
});

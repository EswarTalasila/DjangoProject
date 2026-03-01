import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

async function loadDialog() {
  vi.resetModules();
  const mod = await import('@/components/codes/CreateRegistrationCodeDialog');
  return mod.CreateRegistrationCodeDialog;
}

describe('CreateRegistrationCodeDialog', () => {
  let onSubmit: ReturnType<typeof vi.fn>;
  let onOpenChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    onSubmit = vi.fn().mockResolvedValue(undefined);
    onOpenChange = vi.fn();
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

    expect(screen.getByLabelText('Code type')).toBeInTheDocument();
    expect(screen.getByLabelText('Number of codes')).toBeInTheDocument();
    expect(screen.getByLabelText('Uses per code')).toBeInTheDocument();
    expect(screen.getByLabelText('Expires at')).toBeInTheDocument();
  });

  it('hides code type selector when hideCodeType is true', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        hideCodeType
        onSubmit={onSubmit}
      />,
    );

    expect(screen.queryByLabelText('Code type')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Number of codes')).toBeInTheDocument();
  });

  it('submits with correct payload including count', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        title="Test"
        description="Desc"
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        hideCodeType
        onSubmit={onSubmit}
      />,
    );

    const user = userEvent.setup();

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
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        hideCodeType
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
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        hideCodeType
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
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        hideCodeType
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
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
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
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByLabelText('Number of codes')).toBeDisabled();
    expect(screen.getByLabelText('Uses per code')).toBeDisabled();
    expect(screen.getByLabelText('Expires at')).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Create code' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeDisabled();
  });
});

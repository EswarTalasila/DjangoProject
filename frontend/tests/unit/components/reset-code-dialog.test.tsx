import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, beforeEach, describe, expect, it, vi } from 'vitest';

async function loadDialog() {
  vi.resetModules();
  const mod = await import('@/components/codes/ResetCodeDialog');
  return mod.ResetCodeDialog;
}

const mockWriteText = vi.fn().mockResolvedValue(undefined);
const originalClipboard = navigator.clipboard;

function setClipboardMock() {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText: mockWriteText },
    writable: true,
    configurable: true,
  });
}

afterAll(() => {
  Object.defineProperty(navigator, 'clipboard', {
    value: originalClipboard,
    writable: true,
    configurable: true,
  });
});

describe('ResetCodeDialog', () => {
  let onOpenChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    setClipboardMock();
    onOpenChange = vi.fn();
    mockWriteText.mockResolvedValue(undefined);
  });

  it('renders code and target name', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code="RST-ABC-123"
        targetName="Jane Smith"
        expiresAt={null}
      />,
    );

    expect(screen.getByText('Password Reset Code')).toBeInTheDocument();
    expect(screen.getByText('RST-ABC-123')).toBeInTheDocument();
    expect(screen.getByText(/Jane Smith/)).toBeInTheDocument();
  });

  it('renders generic description when targetName is null', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code="RST-ABC-123"
        targetName={null}
        expiresAt={null}
      />,
    );

    expect(screen.getByText(/Share this code securely with the target user/)).toBeInTheDocument();
  });

  it('shows "No code available" when code is null', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code={null}
        targetName="Jane Smith"
        expiresAt={null}
      />,
    );

    expect(screen.getByText('No code available')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy code/i })).toBeDisabled();
  });

  it('shows default expiry text when expiresAt is null', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code="RST-ABC-123"
        targetName="Jane"
        expiresAt={null}
      />,
    );

    expect(screen.getByText('Expires in 30 minutes.')).toBeInTheDocument();
  });

  it('shows expiry in minutes for a future date', async () => {
    const Dialog = await loadDialog();
    const futureDate = new Date(Date.now() + 15 * 60 * 1000).toISOString();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code="RST-ABC-123"
        targetName="Jane"
        expiresAt={futureDate}
      />,
    );

    expect(screen.getByText(/Expires in approximately \d+ minutes?/)).toBeInTheDocument();
  });

  it('shows expired text for a past date', async () => {
    const Dialog = await loadDialog();
    const pastDate = new Date(Date.now() - 60 * 1000).toISOString();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code="RST-ABC-123"
        targetName="Jane"
        expiresAt={pastDate}
      />,
    );

    expect(screen.getByText('This code is now expired.')).toBeInTheDocument();
  });

  it('copy button is enabled when code is present', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code="RST-ABC-123"
        targetName="Jane"
        expiresAt={null}
      />,
    );

    expect(screen.getByRole('button', { name: /Copy code/i })).not.toBeDisabled();
  });

  it('close button calls onOpenChange(false)', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code="RST-ABC-123"
        targetName="Jane"
        expiresAt={null}
      />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Close dialog' }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('shows one-time-use warning', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        code="RST-ABC-123"
        targetName="Jane"
        expiresAt={null}
      />,
    );

    expect(screen.getByText(/one-time use/)).toBeInTheDocument();
  });
});

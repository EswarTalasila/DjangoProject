import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterAll, beforeEach, describe, expect, it, vi } from 'vitest';

async function loadDialog() {
  vi.resetModules();
  const mod = await import('@/components/codes/RegistrationCodeDialog');
  return mod.RegistrationCodeDialog;
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

describe('RegistrationCodeDialog', () => {
  let onOpenChange: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.clearAllMocks();
    setClipboardMock();
    onOpenChange = vi.fn();
    mockWriteText.mockResolvedValue(undefined);
  });

  it('renders single code with singular title', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog open={true} onOpenChange={onOpenChange} codes={['REG-ABC-123']} />,
    );

    expect(screen.getByText('Registration Code')).toBeInTheDocument();
    expect(screen.getByText('REG-ABC-123')).toBeInTheDocument();
    expect(screen.getByText('Code')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy code/i })).toBeInTheDocument();
  });

  it('renders multiple codes with plural title and count', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        codes={['REG-AAA-111', 'REG-BBB-222', 'REG-CCC-333']}
      />,
    );

    expect(screen.getByText('Registration Codes')).toBeInTheDocument();
    expect(screen.getByText('Codes (3)')).toBeInTheDocument();
    expect(screen.getByText('REG-AAA-111')).toBeInTheDocument();
    expect(screen.getByText('REG-BBB-222')).toBeInTheDocument();
    expect(screen.getByText('REG-CCC-333')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy all/i })).toBeInTheDocument();
  });

  it('renders empty state when no codes', async () => {
    const Dialog = await loadDialog();
    render(<Dialog open={true} onOpenChange={onOpenChange} codes={[]} />);

    expect(screen.getByText('No code available')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Copy code/i })).toBeDisabled();
  });

  it('copy button is enabled for single code', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog open={true} onOpenChange={onOpenChange} codes={['REG-ABC-123']} />,
    );

    expect(screen.getByRole('button', { name: /Copy code/i })).not.toBeDisabled();
  });

  it('copy all button is enabled for multiple codes', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        codes={['REG-AAA-111', 'REG-BBB-222']}
      />,
    );

    expect(screen.getByRole('button', { name: /Copy all/i })).not.toBeDisabled();
  });

  it('close button calls onOpenChange(false)', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog open={true} onOpenChange={onOpenChange} codes={['REG-ABC-123']} />,
    );

    const user = userEvent.setup();
    await user.click(screen.getByRole('button', { name: 'Close dialog' }));

    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('shows security warning for single code', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog open={true} onOpenChange={onOpenChange} codes={['REG-ABC-123']} />,
    );

    expect(
      screen.getByText(/This code cannot be retrieved again/),
    ).toBeInTheDocument();
  });

  it('shows security warning for multiple codes', async () => {
    const Dialog = await loadDialog();
    render(
      <Dialog
        open={true}
        onOpenChange={onOpenChange}
        codes={['REG-AAA', 'REG-BBB']}
      />,
    );

    expect(
      screen.getByText(/These codes cannot be retrieved again/),
    ).toBeInTheDocument();
  });
});

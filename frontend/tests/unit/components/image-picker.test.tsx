import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import ImagePicker from '@/components/media/ImagePicker';

describe('ImagePicker', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('opens the file chooser from the visible button', async () => {
    const user = userEvent.setup();
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, 'click');

    render(
      <ImagePicker
        image={null}
        onSelect={vi.fn()}
        onRemove={vi.fn()}
        onUpload={vi.fn()}
      />,
    );

    await user.click(screen.getByRole('button', { name: 'Choose File' }));

    expect(clickSpy).toHaveBeenCalled();
  });

  it('opens the file chooser when the drop zone is clicked', async () => {
    const user = userEvent.setup();
    const clickSpy = vi.spyOn(HTMLInputElement.prototype, 'click');

    render(
      <ImagePicker
        image={null}
        onSelect={vi.fn()}
        onRemove={vi.fn()}
        onUpload={vi.fn()}
      />,
    );

    await user.click(
      screen.getByRole('button', {
        name: 'Drop an image here or click to upload',
      }),
    );

    expect(clickSpy).toHaveBeenCalled();
  });

  it('uploads a selected file and forwards the picked image', async () => {
    const onSelect = vi.fn();
    const onUpload = vi.fn().mockResolvedValue({
      id: 'img-1',
      url: '/demo.png',
      originalFilename: 'demo.png',
      mimeType: 'image/png',
      sizeBytes: 1234,
    });

    render(
      <ImagePicker
        image={null}
        onSelect={onSelect}
        onRemove={vi.fn()}
        onUpload={onUpload}
      />,
    );

    const input = screen.getByLabelText('Upload image file');
    const file = new File(['demo'], 'demo.png', { type: 'image/png' });

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(onUpload).toHaveBeenCalledWith(file);
      expect(onSelect).toHaveBeenCalledWith({
        id: 'img-1',
        url: '/demo.png',
        originalFilename: 'demo.png',
        mimeType: 'image/png',
        sizeBytes: 1234,
      });
    });
  });
});

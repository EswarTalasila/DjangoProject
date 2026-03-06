import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { cn, toErrorMessage, triggerBrowserDownload } from '@/lib/utils';

describe('cn', () => {
  it('merges duplicate tailwind classes', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4');
  });

  it('ignores falsy values', () => {
    expect(cn('text-sm', undefined, false && 'hidden')).toBe('text-sm');
  });

  it('combines multiple class names', () => {
    expect(cn('text-sm', 'font-bold')).toBe('text-sm font-bold');
  });

  it('handles empty input', () => {
    expect(cn()).toBe('');
  });

  it('handles conditional classes', () => {
    const isActive = true;
    const isDisabled = false;
    expect(cn('base', isActive && 'active', isDisabled && 'disabled')).toBe('base active');
  });
});

describe('toErrorMessage', () => {
  it('extracts detail from Axios error response', () => {
    const error = {
      response: { data: { detail: 'Something went wrong' } },
    };
    expect(toErrorMessage(error)).toBe('Something went wrong');
  });

  it('returns default message for null error', () => {
    expect(toErrorMessage(null)).toBe('Unexpected error.');
  });

  it('returns default message for undefined error', () => {
    expect(toErrorMessage(undefined)).toBe('Unexpected error.');
  });

  it('returns default message for error without response', () => {
    expect(toErrorMessage(new Error('fail'))).toBe('Unexpected error.');
  });

  it('returns default message when response has no data', () => {
    expect(toErrorMessage({ response: {} })).toBe('Unexpected error.');
  });

  it('returns default message when data has no detail', () => {
    expect(toErrorMessage({ response: { data: {} } })).toBe('Unexpected error.');
  });

  it('returns default message for string error', () => {
    expect(toErrorMessage('just a string')).toBe('Unexpected error.');
  });
});

describe('triggerBrowserDownload', () => {
  let createObjectURLSpy: ReturnType<typeof vi.spyOn>;
  let revokeObjectURLSpy: ReturnType<typeof vi.spyOn>;
  let appendChildSpy: ReturnType<typeof vi.spyOn>;
  let clickSpy: ReturnType<typeof vi.fn>;
  let removeSpy: ReturnType<typeof vi.fn>;
  let createElementSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    createObjectURLSpy = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test-url');
    revokeObjectURLSpy = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
    clickSpy = vi.fn();
    removeSpy = vi.fn();
    const fakeLink = {
      href: '',
      download: '',
      click: clickSpy,
      remove: removeSpy,
    };
    createElementSpy = vi.spyOn(document, 'createElement').mockReturnValue(fakeLink as unknown as HTMLElement);
    appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation((node) => node);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates an object URL, clicks a link, and cleans up', () => {
    const blob = new Blob(['test'], { type: 'text/plain' });
    triggerBrowserDownload(blob, 'test.txt');

    expect(createObjectURLSpy).toHaveBeenCalledWith(blob);
    expect(createElementSpy).toHaveBeenCalledWith('a');
    expect(appendChildSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(removeSpy).toHaveBeenCalled();
    expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:test-url');
  });
});

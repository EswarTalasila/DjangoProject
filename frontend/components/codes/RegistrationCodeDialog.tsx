'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, Copy } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';

type RegistrationCodeDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  codes: string[];
};

export function RegistrationCodeDialog({
  open,
  onOpenChange,
  codes,
}: RegistrationCodeDialogProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) setCopied(false);
  }, [open]);

  const hasMultiple = codes.length > 1;

  async function handleCopy() {
    if (codes.length === 0) return;
    await navigator.clipboard.writeText(codes.join('\n'));
    setCopied(true);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {hasMultiple ? 'Registration Codes' : 'Registration Code'}
          </DialogTitle>
          <DialogDescription>
            {hasMultiple
              ? 'Save these codes now. For security, plaintext registration codes are only shown at creation.'
              : 'Save this code now. For security, plaintext registration codes are only shown at creation.'}
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-md border bg-slate-50 p-4">
          <p className="mb-2 text-xs font-medium uppercase text-slate-500">
            {hasMultiple ? `Codes (${codes.length})` : 'Code'}
          </p>
          {codes.length === 0 ? (
            <p className="font-mono text-lg font-semibold tracking-wide text-slate-900">
              No code available
            </p>
          ) : hasMultiple ? (
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {codes.map((code, index) => (
                <p
                  key={index}
                  className="font-mono text-sm font-semibold tracking-wide text-slate-900"
                >
                  {code}
                </p>
              ))}
            </div>
          ) : (
            <p className="font-mono text-lg font-semibold tracking-wide text-slate-900">
              {codes[0]}
            </p>
          )}
        </div>

        <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="text-xs">
            {hasMultiple
              ? 'These codes cannot be retrieved again after closing this dialog. Copy them and share them securely.'
              : 'This code cannot be retrieved again after closing this dialog. Copy it and share it securely.'}
          </p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={handleCopy} disabled={codes.length === 0}>
            <Copy className="mr-2 h-4 w-4" />
            {copied ? 'Copied' : hasMultiple ? 'Copy all' : 'Copy code'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

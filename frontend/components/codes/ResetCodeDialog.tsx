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

type ResetCodeDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  code: string | null;
  targetName?: string | null;
  expiresAt?: string | null;
};

export function ResetCodeDialog({
  open,
  onOpenChange,
  code,
  targetName,
  expiresAt,
}: ResetCodeDialogProps) {
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (!open) setCopied(false);
  }, [open]);

  async function handleCopy() {
    if (!code) return;
    await navigator.clipboard.writeText(code);
    setCopied(true);
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Password Reset Code</DialogTitle>
          <DialogDescription>
            {targetName ? `Share this code with ${targetName}.` : 'Share this reset code securely.'}
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-md border bg-slate-50 p-4">
          <p className="mb-2 text-xs font-medium uppercase text-slate-500">Code</p>
          <p className="font-mono text-lg font-semibold tracking-wide text-slate-900">
            {code ?? 'No code available'}
          </p>
          {expiresAt ? (
            <p className="mt-2 text-xs text-slate-500">Expires at: {new Date(expiresAt).toLocaleString()}</p>
          ) : null}
        </div>

        <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <p className="text-xs">This reset code is one-time use and expires in 30 minutes.</p>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button onClick={handleCopy} disabled={!code}>
            <Copy className="mr-2 h-4 w-4" />
            {copied ? 'Copied' : 'Copy code'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

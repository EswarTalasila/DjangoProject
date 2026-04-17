"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, Copy } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type ResetCodeDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  code: string | null;
  targetName: string | null;
  expiresAt: string | null;
};

function formatExpiry(expiresAt: string | null): string {
  if (!expiresAt) return "Expires in 30 minutes.";
  const parsed = Date.parse(expiresAt);
  if (Number.isNaN(parsed)) return "Expires in 30 minutes.";
  const minutes = Math.max(0, Math.ceil((parsed - Date.now()) / 60000));
  if (minutes <= 0) return "This code is now expired.";
  return `Expires in approximately ${minutes} minute${minutes === 1 ? "" : "s"}.`;
}

export function ResetCodeDialog({
  open,
  onOpenChange,
  code,
  targetName,
  expiresAt,
}: ResetCodeDialogProps) {
  const [copied, setCopied] = useState(false);
  const expiryText = useMemo(() => formatExpiry(expiresAt), [expiresAt, open]);

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
            {targetName
              ? `Share this code securely with ${targetName}.`
              : "Share this code securely with the target user."}
          </DialogDescription>
        </DialogHeader>

        <div className="rounded-md border bg-slate-50 p-4">
          <p className="mb-2 text-xs font-medium uppercase text-slate-500">Code</p>
          <p className="font-mono text-lg font-semibold tracking-wide text-slate-900">
            {code ?? "No code available"}
          </p>
        </div>

        <div className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-amber-900">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div className="text-xs">
            <p>This code is one-time use and cannot be recovered after this dialog closes.</p>
            <p className="mt-1">{expiryText}</p>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} aria-label="Close dialog">
            Close
          </Button>
          <Button onClick={handleCopy} disabled={!code}>
            <Copy className="mr-2 h-4 w-4" />
            {copied ? "Copied" : "Copy code"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

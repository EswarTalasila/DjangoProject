'use client';

import { Archive, ShieldOff } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import type { RegistrationCode, RegistrationCodeStatus } from '@/lib/registration-code-api';

const STATUS_COLORS: Record<RegistrationCodeStatus, string> = {
  ACTIVE: 'bg-status-success-bg text-status-success',
  EXHAUSTED: 'bg-muted text-muted-foreground',
  EXPIRED: 'bg-status-warning-bg text-status-warning',
  REVOKED: 'bg-status-error-bg text-status-error',
  ARCHIVED: 'bg-muted text-muted-foreground',
};

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

type CodeDetailDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  code: RegistrationCode | null;
  onRevoke: (code: RegistrationCode) => Promise<void>;
  onArchive: (code: RegistrationCode) => Promise<void>;
  isActionLoading: boolean;
};

export function CodeDetailDialog({
  open,
  onOpenChange,
  code,
  onRevoke,
  onArchive,
  isActionLoading,
}: CodeDetailDialogProps) {
  if (!code) return null;

  const canRevoke = code.status === 'ACTIVE';
  const canArchive =
    code.status === 'EXHAUSTED' ||
    code.status === 'EXPIRED' ||
    code.status === 'REVOKED';

  const metadata = code.metadata && Object.keys(code.metadata).length > 0 ? code.metadata : null;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Code Details</DialogTitle>
          <DialogDescription>
            Registration code {code.codePrefix}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
            <div>
              <p className="font-medium text-muted-foreground">Prefix</p>
              <p className="font-mono text-foreground">{code.codePrefix}</p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Type</p>
              <p className="text-foreground">
                {code.codeType.charAt(0) + code.codeType.slice(1).toLowerCase()}
              </p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Status</p>
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[code.status]}`}
              >
                {code.status}
              </span>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Uses</p>
              <p className="text-foreground">
                {code.timesUsed}/{code.maxUses} ({code.usesRemaining} remaining)
              </p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Course</p>
              <p className="text-foreground">{code.courseName ?? '-'}</p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Created By</p>
              <p className="text-foreground">User #{code.createdByUserId}</p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Created</p>
              <p className="text-foreground">{formatDateTime(code.createdAt)}</p>
            </div>
            <div>
              <p className="font-medium text-muted-foreground">Expires</p>
              <p className="text-foreground">{formatDateTime(code.expiresAt)}</p>
            </div>
            {code.archivedAt && (
              <div className="col-span-2">
                <p className="font-medium text-muted-foreground">Archived</p>
                <p className="text-foreground">{formatDateTime(code.archivedAt)}</p>
              </div>
            )}
          </div>

          {metadata && (
            <div>
              <p className="text-sm font-medium text-muted-foreground mb-1">Metadata</p>
              <div className="rounded border border-border bg-muted p-3">
                {Object.entries(metadata).map(([key, value]) => (
                  <div key={key} className="flex gap-2 text-sm">
                    <span className="font-medium text-foreground">{key}:</span>
                    <span className="text-muted-foreground">{String(value)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          {canRevoke && (
            <Button
              variant="destructive"
              disabled={isActionLoading}
              onClick={() => void onRevoke(code)}
            >
              <ShieldOff className="mr-2 h-4 w-4" />
              Revoke
            </Button>
          )}
          {canArchive && (
            <Button
              variant="outline"
              disabled={isActionLoading}
              onClick={() => void onArchive(code)}
            >
              <Archive className="mr-2 h-4 w-4" />
              Archive
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

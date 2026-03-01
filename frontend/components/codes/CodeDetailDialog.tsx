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
  ACTIVE: 'bg-green-100 text-green-800',
  EXHAUSTED: 'bg-gray-100 text-gray-800',
  EXPIRED: 'bg-yellow-100 text-yellow-800',
  REVOKED: 'bg-red-100 text-red-800',
  ARCHIVED: 'bg-slate-100 text-slate-600',
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
              <p className="font-medium text-[#754d28]">Prefix</p>
              <p className="font-mono text-[#61323e]">{code.codePrefix}</p>
            </div>
            <div>
              <p className="font-medium text-[#754d28]">Type</p>
              <p className="text-[#61323e]">
                {code.codeType.charAt(0) + code.codeType.slice(1).toLowerCase()}
              </p>
            </div>
            <div>
              <p className="font-medium text-[#754d28]">Status</p>
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[code.status]}`}
              >
                {code.status}
              </span>
            </div>
            <div>
              <p className="font-medium text-[#754d28]">Uses</p>
              <p className="text-[#61323e]">
                {code.timesUsed}/{code.maxUses} ({code.usesRemaining} remaining)
              </p>
            </div>
            <div>
              <p className="font-medium text-[#754d28]">Course</p>
              <p className="text-[#61323e]">{code.courseName ?? '-'}</p>
            </div>
            <div>
              <p className="font-medium text-[#754d28]">Created By</p>
              <p className="text-[#61323e]">User #{code.createdByUserId}</p>
            </div>
            <div>
              <p className="font-medium text-[#754d28]">Created</p>
              <p className="text-[#61323e]">{formatDateTime(code.createdAt)}</p>
            </div>
            <div>
              <p className="font-medium text-[#754d28]">Expires</p>
              <p className="text-[#61323e]">{formatDateTime(code.expiresAt)}</p>
            </div>
            {code.archivedAt && (
              <div className="col-span-2">
                <p className="font-medium text-[#754d28]">Archived</p>
                <p className="text-[#61323e]">{formatDateTime(code.archivedAt)}</p>
              </div>
            )}
          </div>

          {metadata && (
            <div>
              <p className="text-sm font-medium text-[#754d28] mb-1">Metadata</p>
              <div className="rounded border border-[#ebe9e7] bg-[#faf9f8] p-3">
                {Object.entries(metadata).map(([key, value]) => (
                  <div key={key} className="flex gap-2 text-sm">
                    <span className="font-medium text-[#61323e]">{key}:</span>
                    <span className="text-[#754d28]">{String(value)}</span>
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

'use client';

import { Archive, Eye, MoreVertical, ShieldOff } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import type { RegistrationCode, RegistrationCodeStatus } from '@/lib/registration-code-api';

const STATUS_COLORS: Record<RegistrationCodeStatus, string> = {
  ACTIVE: 'bg-status-success-bg text-status-success',
  EXHAUSTED: 'bg-muted text-muted-foreground',
  EXPIRED: 'bg-status-warning-bg text-status-warning',
  REVOKED: 'bg-status-error-bg text-status-error',
  ARCHIVED: 'bg-muted text-muted-foreground',
};

function StatusBadge({ status }: { status: RegistrationCodeStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLORS[status]}`}
    >
      {status}
    </span>
  );
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

type CodesTableProps = {
  codes: RegistrationCode[];
  isLoading: boolean;
  loadError: string | null;
  isActionLoading: boolean;
  onViewDetail: (code: RegistrationCode) => void;
  onRevoke: (code: RegistrationCode) => void;
  onArchive: (code: RegistrationCode) => void;
};

export function CodesTable({
  codes,
  isLoading,
  loadError,
  isActionLoading,
  onViewDetail,
  onRevoke,
  onArchive,
}: CodesTableProps) {
  if (loadError) {
    return <p className="text-sm text-destructive">{loadError}</p>;
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground">Loading codes...</p>;
  }

  if (codes.length === 0) {
    return (
      <div className="rounded-sm border border-border p-8 text-center">
        <p className="text-sm text-muted-foreground">No registration codes found.</p>
      </div>
    );
  }

  return (
    <div className="rounded-sm border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted border-b border-border">
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Prefix</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Status</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Uses</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Course</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Expires</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Created</TableHead>
            <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Actions</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {codes.map((code) => {
            const canRevoke = code.status === 'ACTIVE';
            const canArchive =
              code.status === 'EXHAUSTED' ||
              code.status === 'EXPIRED' ||
              code.status === 'REVOKED';
            return (
              <TableRow key={code.id} className="even:bg-muted/50 hover:bg-accent transition-colors">
                <TableCell className="font-mono text-sm text-foreground">
                  {code.codePrefix}
                </TableCell>
                <TableCell>
                  <StatusBadge status={code.status} />
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {code.timesUsed}/{code.maxUses}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {code.courseName ?? '-'}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDate(code.expiresAt)}
                </TableCell>
                <TableCell className="text-sm text-muted-foreground">
                  {formatDate(code.createdAt)}
                </TableCell>
                <TableCell>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        className="h-8 w-8 p-0 text-muted-foreground"
                        disabled={isActionLoading}
                      >
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => onViewDetail(code)}>
                        <Eye className="mr-2 h-4 w-4" />
                        View Details
                      </DropdownMenuItem>
                      {canRevoke && (
                        <DropdownMenuItem onClick={() => onRevoke(code)}>
                          <ShieldOff className="mr-2 h-4 w-4" />
                          Revoke
                        </DropdownMenuItem>
                      )}
                      {canArchive && (
                        <DropdownMenuItem onClick={() => onArchive(code)}>
                          <Archive className="mr-2 h-4 w-4" />
                          Archive
                        </DropdownMenuItem>
                      )}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

'use client';

import { Eye, MoreVertical, ShieldOff, Trash2 } from 'lucide-react';

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
import { formatShortDate } from '@/lib/utils';

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


type CodesTableProps = {
  codes: RegistrationCode[];
  isLoading: boolean;
  loadError: string | null;
  isActionLoading: boolean;
  onViewDetail: (code: RegistrationCode) => void;
  onRevoke: (code: RegistrationCode) => void;
  onDelete: (code: RegistrationCode) => void;
};

export function CodesTable({
  codes,
  isLoading,
  loadError,
  isActionLoading,
  onViewDetail,
  onRevoke,
  onDelete,
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
    <div className="overflow-hidden rounded-sm border border-border">
      <div className="grid gap-3 p-3 md:hidden">
        {codes.map((code) => {
          const canRevoke = code.status === 'ACTIVE';
          return (
            <article
              key={code.id}
              className="rounded-xl border border-border bg-background p-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-mono text-sm font-medium text-foreground">
                    {code.codePrefix}
                  </p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {code.courseName ?? 'No linked course'}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={code.status} />
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        className="h-8 w-8 shrink-0 p-0 text-muted-foreground"
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
                      <DropdownMenuItem onClick={() => onDelete(code)}>
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </div>

              <dl className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
                <div>
                  <dt className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Uses
                  </dt>
                  <dd className="mt-1 text-foreground">
                    {code.timesUsed}/{code.maxUses}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Expires
                  </dt>
                  <dd className="mt-1 text-foreground">
                    {formatShortDate(code.expiresAt)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Created
                  </dt>
                  <dd className="mt-1 text-foreground">
                    {formatShortDate(code.createdAt)}
                  </dd>
                </div>
                <div>
                  <dt className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
                    Type
                  </dt>
                  <dd className="mt-1 text-foreground">{code.codeType}</dd>
                </div>
              </dl>
            </article>
          );
        })}
      </div>

      <div className="hidden md:block">
        <Table>
          <TableHeader>
            <TableRow className="border-b border-border bg-muted">
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
              return (
                <TableRow
                  key={code.id}
                  className="transition-colors even:bg-muted/50 hover:bg-accent"
                >
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
                    {formatShortDate(code.expiresAt)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatShortDate(code.createdAt)}
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
                        <DropdownMenuItem onClick={() => onDelete(code)}>
                          <Trash2 className="mr-2 h-4 w-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

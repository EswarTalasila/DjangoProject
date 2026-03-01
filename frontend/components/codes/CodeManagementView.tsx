'use client';

import { useCallback, useEffect, useState } from 'react';
import { Archive, Eye, MoreVertical, Plus, ShieldOff } from 'lucide-react';
import { toast } from 'sonner';

import { CodeDetailDialog } from '@/components/codes/CodeDetailDialog';
import { CreateRegistrationCodeDialog } from '@/components/codes/CreateRegistrationCodeDialog';
import { RegistrationCodeDialog } from '@/components/codes/RegistrationCodeDialog';
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
import {
  createRegistrationCodes,
  listRegistrationCodes,
  updateRegistrationCodeStatus,
  type RegistrationCode,
  type RegistrationCodeStatus,
  type RegistrationCodeType,
} from '@/lib/registration-code-api';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

const STATUS_COLORS: Record<RegistrationCodeStatus, string> = {
  ACTIVE: 'bg-green-100 text-green-800',
  EXHAUSTED: 'bg-gray-100 text-gray-800',
  EXPIRED: 'bg-yellow-100 text-yellow-800',
  REVOKED: 'bg-red-100 text-red-800',
  ARCHIVED: 'bg-slate-100 text-slate-600',
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

type CodeManagementViewProps = {
  userRole: 'TEACHER' | 'RESEARCHER';
};

export default function CodeManagementView({ userRole }: CodeManagementViewProps) {
  const [codes, setCodes] = useState<RegistrationCode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<RegistrationCodeStatus | ''>('');
  const [codeTypeFilter, setCodeTypeFilter] = useState<RegistrationCodeType | ''>('');
  const [showArchived, setShowArchived] = useState(false);

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [createdCodes, setCreatedCodes] = useState<string[]>([]);
  const [isCodeDialogOpen, setIsCodeDialogOpen] = useState(false);

  const [detailCode, setDetailCode] = useState<RegistrationCode | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const allowedCodeTypes: RegistrationCodeType[] =
    userRole === 'RESEARCHER' ? ['STUDENT', 'TEACHER', 'RESEARCHER'] : ['STUDENT'];
  const codeTypeFilterOptions: RegistrationCodeType[] =
    userRole === 'RESEARCHER' ? ['STUDENT', 'TEACHER', 'RESEARCHER'] : ['STUDENT'];

  const loadCodes = useCallback(async () => {
    setLoadError(null);
    try {
      const response = await listRegistrationCodes({
        status: statusFilter || undefined,
        codeType: codeTypeFilter || undefined,
        includeArchived: showArchived,
      });
      setCodes(response.results);
    } catch {
      setLoadError('Failed to load registration codes.');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, codeTypeFilter, showArchived]);

  useEffect(() => {
    setIsLoading(true);
    void loadCodes();
  }, [loadCodes]);

  async function handleCreateCode(values: {
    codeType: RegistrationCodeType;
    count: number;
    usesPerCode: number;
    expiresAt: string;
  }) {
    setIsActionLoading(true);
    try {
      const response = await createRegistrationCodes({
        codeType: values.codeType,
        count: values.count,
        usesPerCode: values.usesPerCode,
        expiresAt: values.expiresAt,
      });
      const plainCodes = response.codes
        .map((c) => c.code)
        .filter((c): c is string => c != null);
      if (plainCodes.length === 0) throw new Error('No codes returned by the server.');
      setCreatedCodes(plainCodes);
      setIsCreateDialogOpen(false);
      setIsCodeDialogOpen(true);
      await loadCodes();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to generate code.'));
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleRevoke(code: RegistrationCode) {
    setIsActionLoading(true);
    try {
      await updateRegistrationCodeStatus(code.id, 'REVOKED');
      toast.success(`Code ${code.codePrefix} revoked.`);
      await loadCodes();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to revoke code.'));
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleArchive(code: RegistrationCode) {
    setIsActionLoading(true);
    try {
      await updateRegistrationCodeStatus(code.id, 'ARCHIVED');
      toast.success(`Code ${code.codePrefix} archived.`);
      await loadCodes();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to archive code.'));
    } finally {
      setIsActionLoading(false);
    }
  }

  function handleViewDetail(code: RegistrationCode) {
    setDetailCode(code);
    setIsDetailOpen(true);
  }

  return (
    <div className="space-y-6 p-8 max-w-7xl mx-auto">
      <CreateRegistrationCodeDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        isLoading={isActionLoading}
        title="Generate registration code"
        description="Configure the code type, usage limits, and expiration."
        allowedCodeTypes={allowedCodeTypes}
        initialCodeType={allowedCodeTypes[0]}
        hideCodeType={allowedCodeTypes.length === 1}
        onSubmit={async (values) =>
          handleCreateCode({
            codeType: values.codeType,
            count: values.count,
            usesPerCode: values.usesPerCode,
            expiresAt: values.expiresAt,
          })
        }
      />
      <RegistrationCodeDialog
        open={isCodeDialogOpen}
        onOpenChange={setIsCodeDialogOpen}
        codes={createdCodes}
      />
      <CodeDetailDialog
        open={isDetailOpen}
        onOpenChange={setIsDetailOpen}
        code={detailCode}
        onRevoke={handleRevoke}
        onArchive={handleArchive}
        isActionLoading={isActionLoading}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#61323e]">
            Registration Codes
          </h1>
          <p className="text-[#754d28] mt-1">
            Manage registration codes and their lifecycle.
          </p>
        </div>
        <Button
          className="bg-[#2b6ea4] hover:bg-[#205a86] text-white"
          onClick={() => setIsCreateDialogOpen(true)}
          disabled={isActionLoading}
        >
          <Plus className="mr-2 h-4 w-4" />
          Generate Code
        </Button>
      </div>

      <div className="flex items-center gap-4 flex-wrap">
        <div className="flex items-center gap-2">
          <label htmlFor="status-filter" className="text-sm font-medium text-[#754d28]">
            Status
          </label>
          <select
            id="status-filter"
            className="h-9 rounded-md border border-input bg-background px-3 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as RegistrationCodeStatus | '')}
          >
            <option value="">All</option>
            <option value="ACTIVE">Active</option>
            <option value="EXHAUSTED">Exhausted</option>
            <option value="EXPIRED">Expired</option>
            <option value="REVOKED">Revoked</option>
          </select>
        </div>

        {codeTypeFilterOptions.length > 1 && (
          <div className="flex items-center gap-2">
            <label htmlFor="type-filter" className="text-sm font-medium text-[#754d28]">
              Type
            </label>
            <select
              id="type-filter"
              className="h-9 rounded-md border border-input bg-background px-3 text-sm"
              value={codeTypeFilter}
              onChange={(e) => setCodeTypeFilter(e.target.value as RegistrationCodeType | '')}
            >
              <option value="">All</option>
              {codeTypeFilterOptions.map((t) => (
                <option key={t} value={t}>
                  {t.charAt(0) + t.slice(1).toLowerCase()}
                </option>
              ))}
            </select>
          </div>
        )}

        <label className="flex items-center gap-2 text-sm text-[#754d28]">
          <input
            type="checkbox"
            checked={showArchived}
            onChange={(e) => setShowArchived(e.target.checked)}
            className="rounded border-gray-300"
          />
          Show Archived
        </label>
      </div>

      {loadError && <p className="text-sm text-red-600">{loadError}</p>}
      {isLoading && <p className="text-sm text-[#754d28]">Loading codes...</p>}

      {!isLoading && !loadError && codes.length === 0 && (
        <div className="rounded-md border border-[#ebe9e7] p-8 text-center">
          <p className="text-sm text-[#754d28]">No registration codes found.</p>
        </div>
      )}

      {!isLoading && codes.length > 0 && (
        <div className="rounded-md border border-[#ebe9e7]">
          <Table>
            <TableHeader>
              <TableRow className="bg-[#faf9f8]">
                <TableHead className="text-[#754d28]">Prefix</TableHead>
                <TableHead className="text-[#754d28]">Type</TableHead>
                <TableHead className="text-[#754d28]">Status</TableHead>
                <TableHead className="text-[#754d28]">Uses</TableHead>
                <TableHead className="text-[#754d28]">Course</TableHead>
                <TableHead className="text-[#754d28]">Expires</TableHead>
                <TableHead className="text-[#754d28]">Created</TableHead>
                <TableHead className="text-[#754d28]">Actions</TableHead>
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
                  <TableRow key={code.id}>
                    <TableCell className="font-mono text-sm text-[#61323e]">
                      {code.codePrefix}
                    </TableCell>
                    <TableCell className="text-sm text-[#754d28]">
                      {code.codeType.charAt(0) + code.codeType.slice(1).toLowerCase()}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={code.status} />
                    </TableCell>
                    <TableCell className="text-sm text-[#754d28]">
                      {code.timesUsed}/{code.maxUses}
                    </TableCell>
                    <TableCell className="text-sm text-[#754d28]">
                      {code.courseName ?? '-'}
                    </TableCell>
                    <TableCell className="text-sm text-[#754d28]">
                      {formatDate(code.expiresAt)}
                    </TableCell>
                    <TableCell className="text-sm text-[#754d28]">
                      {formatDate(code.createdAt)}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            className="h-8 w-8 p-0 text-[#754d28]"
                            disabled={isActionLoading}
                          >
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleViewDetail(code)}>
                            <Eye className="mr-2 h-4 w-4" />
                            View Details
                          </DropdownMenuItem>
                          {canRevoke && (
                            <DropdownMenuItem onClick={() => void handleRevoke(code)}>
                              <ShieldOff className="mr-2 h-4 w-4" />
                              Revoke
                            </DropdownMenuItem>
                          )}
                          {canArchive && (
                            <DropdownMenuItem onClick={() => void handleArchive(code)}>
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
      )}
    </div>
  );
}

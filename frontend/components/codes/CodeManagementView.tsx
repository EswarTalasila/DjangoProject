'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { CodeDetailDialog } from '@/components/codes/CodeDetailDialog';
import { CodeTypeTabs } from '@/components/codes/CodeTypeTabs';
import { CodesTable } from '@/components/codes/CodesTable';
import { CodesToolbar } from '@/components/codes/CodesToolbar';
import { CreateRegistrationCodeDialog } from '@/components/codes/CreateRegistrationCodeDialog';
import { RegistrationCodeDialog } from '@/components/codes/RegistrationCodeDialog';
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

type CodeManagementViewProps = {
  userRole: 'TEACHER' | 'RESEARCHER';
  researcherPermissions?: string[];
  isStaff?: boolean;
};

export default function CodeManagementView({
  userRole,
  researcherPermissions = [],
  isStaff = false,
}: CodeManagementViewProps) {
  const canCreateStudentCodes =
    userRole === 'TEACHER' ||
    (userRole === 'RESEARCHER' &&
      (isStaff || researcherPermissions.includes('ISSUE_STUDENT_REG_CODE')));
  const canCreateResearcherCodes =
    userRole === 'RESEARCHER' &&
    (isStaff || researcherPermissions.includes('ISSUE_RESEARCHER_REG_CODE'));

  const allowedCodeTypes: RegistrationCodeType[] = useMemo(() => {
    if (userRole === 'TEACHER') return ['STUDENT'];
    const types: RegistrationCodeType[] = [];
    if (canCreateStudentCodes) types.push('STUDENT');
    types.push('TEACHER');
    if (canCreateResearcherCodes) types.push('RESEARCHER');
    return types;
  }, [userRole, canCreateStudentCodes, canCreateResearcherCodes]);

  const [activeTab, setActiveTab] = useState<RegistrationCodeType>(allowedCodeTypes[0]);
  const [statusFilter, setStatusFilter] = useState<RegistrationCodeStatus | ''>('');
  const [codes, setCodes] = useState<RegistrationCode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [createdCodes, setCreatedCodes] = useState<string[]>([]);
  const [isCodeDialogOpen, setIsCodeDialogOpen] = useState(false);

  const [detailCode, setDetailCode] = useState<RegistrationCode | null>(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  const includeArchived = statusFilter === 'ARCHIVED';

  const loadCodes = useCallback(async () => {
    setLoadError(null);
    try {
      const response = await listRegistrationCodes({
        status: statusFilter || undefined,
        codeType: activeTab,
        includeArchived,
      });
      setCodes(response.results);
    } catch {
      setLoadError('Failed to load registration codes.');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter, activeTab, includeArchived]);

  useEffect(() => {
    setIsLoading(true);
    void loadCodes();
  }, [loadCodes]);

  function handleTabChange(tab: RegistrationCodeType) {
    setActiveTab(tab);
    setStatusFilter('');
  }

  async function handleCreateCode(values: {
    codeType: RegistrationCodeType;
    count: number;
    usesPerCode: number;
    expiresAt: string;
    courseId?: number;
  }) {
    setIsActionLoading(true);
    try {
      const response = await createRegistrationCodes({
        codeType: values.codeType,
        count: values.count,
        usesPerCode: values.usesPerCode,
        expiresAt: values.expiresAt,
        courseId: values.courseId,
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

  return (
    <div className="space-y-6 p-6 max-w-6xl mx-auto">
      <CreateRegistrationCodeDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        isLoading={isActionLoading}
        title="Generate registration code"
        description="Configure the code type, usage limits, and expiration."
        allowedCodeTypes={[activeTab]}
        initialCodeType={activeTab}
        lockCodeType
        onSubmit={async (values) =>
          handleCreateCode({
            codeType: values.codeType,
            count: values.count,
            usesPerCode: values.usesPerCode,
            expiresAt: values.expiresAt,
            courseId: values.courseId,
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

      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Registration Codes
        </h1>
        <p className="text-muted-foreground mt-1">
          Manage registration codes and their lifecycle.
        </p>
      </div>

      <CodeTypeTabs
        tabs={allowedCodeTypes}
        activeTab={activeTab}
        onTabChange={handleTabChange}
      />

      <CodesToolbar
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        onGenerateClick={() => setIsCreateDialogOpen(true)}
        isActionLoading={isActionLoading}
      />

      <CodesTable
        codes={codes}
        isLoading={isLoading}
        loadError={loadError}
        isActionLoading={isActionLoading}
        onViewDetail={(code) => {
          setDetailCode(code);
          setIsDetailOpen(true);
        }}
        onRevoke={(code) => void handleRevoke(code)}
        onArchive={(code) => void handleArchive(code)}
      />
    </div>
  );
}

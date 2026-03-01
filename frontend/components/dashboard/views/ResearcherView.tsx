'use client';

import { useEffect, useMemo, useState } from 'react';
import { BookOpen, ClipboardCheck, Search, Users } from 'lucide-react';
import { toast } from 'sonner';

import { CreateRegistrationCodeDialog } from '@/components/codes/CreateRegistrationCodeDialog';
import { RegistrationCodeDialog } from '@/components/codes/RegistrationCodeDialog';
import { ResetCodeDialog } from '@/components/codes/ResetCodeDialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { listCourses } from '@/lib/course-api';
import {
  getMySudoGrant,
  issuePasswordResetCode,
  listStaffUsers,
  type MySudoGrantResponse,
  type StaffUser,
} from '@/lib/password-reset-api';
import { createRegistrationCodes } from '@/lib/registration-code-api';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  const detail = (error as ApiError).response?.data?.detail;
  return detail || fallback;
}

export default function ResearcherView() {
  const [isLoading, setIsLoading] = useState(true);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [teachers, setTeachers] = useState<StaffUser[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [courseCount, setCourseCount] = useState(0);
  const [sudoGrant, setSudoGrant] = useState<MySudoGrantResponse | null>(null);

  const [resetCode, setResetCode] = useState<string | null>(null);
  const [resetTargetName, setResetTargetName] = useState<string | null>(null);
  const [resetExpiresAt, setResetExpiresAt] = useState<string | null>(null);
  const [isResetDialogOpen, setIsResetDialogOpen] = useState(false);
  const [registrationCodes, setRegistrationCodes] = useState<string[]>([]);
  const [isRegistrationCodeDialogOpen, setIsRegistrationCodeDialogOpen] = useState(false);
  const [isCreateCodeDialogOpen, setIsCreateCodeDialogOpen] = useState(false);

  const filteredTeachers = useMemo(() => {
    const needle = search.trim().toLowerCase();
    if (!needle) return teachers;
    return teachers.filter((teacher) => {
      const name = teacher.name.toLowerCase();
      const username = teacher.username.toLowerCase();
      const email = (teacher.email || '').toLowerCase();
      return name.includes(needle) || username.includes(needle) || email.includes(needle);
    });
  }, [teachers, search]);

  useEffect(() => {
    async function load() {
      setLoadError(null);
      try {
        const [staff, courses, myGrant] = await Promise.all([
          listStaffUsers(),
          listCourses(),
          getMySudoGrant(),
        ]);
        setTeachers(staff.filter((user) => user.role === 'TEACHER'));
        setCourseCount(courses.length);
        setSudoGrant(myGrant);
      } catch {
        setLoadError('Failed to load researcher dashboard data.');
      } finally {
        setIsLoading(false);
      }
    }

    void load();
  }, []);

  async function handleIssueResetCode(target: StaffUser) {
    setIsActionLoading(true);
    try {
      const response = await issuePasswordResetCode(target.id);
      setResetCode(response.resetCode);
      setResetTargetName(target.name);
      setResetExpiresAt(response.expiresAt);
      setIsResetDialogOpen(true);
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to issue reset code.'));
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleGenerateInviteCode(config: {
    codeType: 'TEACHER' | 'RESEARCHER';
    count: number;
    usesPerCode: number;
    expiresAt: string;
  }) {
    setIsActionLoading(true);
    try {
      const response = await createRegistrationCodes({
        codeType: config.codeType,
        count: config.count,
        usesPerCode: config.usesPerCode,
        expiresAt: config.expiresAt,
      });
      const plainCodes = response.codes
        .map((c) => c.code)
        .filter((c): c is string => c != null);
      if (plainCodes.length === 0) throw new Error('Registration code was not returned by the server.');
      setRegistrationCodes(plainCodes);
      setIsCreateCodeDialogOpen(false);
      setIsRegistrationCodeDialogOpen(true);
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to generate invite code.'));
    } finally {
      setIsActionLoading(false);
    }
  }

  const stats = [
    { label: 'Teachers', value: String(teachers.length), icon: Users, color: 'text-[#2b6ea4]' },
    { label: 'Active Courses', value: String(courseCount), icon: BookOpen, color: 'text-[#61323e]' },
    {
      label: 'Reset Capability',
      value: 'Teacher',
      icon: ClipboardCheck,
      color: 'text-[#754d28]',
    },
  ];
  const canCreateResearcherCodes = Boolean(
    sudoGrant?.isStaff || sudoGrant?.permissions.includes('CREATE_RESEARCHER_CODES'),
  );
  const allowedCodeTypes: Array<'TEACHER' | 'RESEARCHER'> = canCreateResearcherCodes
    ? ['TEACHER', 'RESEARCHER']
    : ['TEACHER'];

  return (
    <div className="space-y-8 p-8 max-w-7xl mx-auto">
      <CreateRegistrationCodeDialog
        open={isCreateCodeDialogOpen}
        onOpenChange={setIsCreateCodeDialogOpen}
        isLoading={isActionLoading}
        title="Generate invite code"
        description={
          canCreateResearcherCodes
            ? 'Set usage amount and expiration for teacher or researcher invite codes.'
            : 'Set usage amount and expiration for teacher invite codes.'
        }
        allowedCodeTypes={allowedCodeTypes}
        initialCodeType="TEACHER"
        onSubmit={async (values) =>
          handleGenerateInviteCode({
            codeType: values.codeType as 'TEACHER' | 'RESEARCHER',
            count: values.count,
            usesPerCode: values.usesPerCode,
            expiresAt: values.expiresAt,
          })
        }
      />
      <RegistrationCodeDialog
        open={isRegistrationCodeDialogOpen}
        onOpenChange={setIsRegistrationCodeDialogOpen}
        codes={registrationCodes}
      />
      <ResetCodeDialog
        open={isResetDialogOpen}
        onOpenChange={setIsResetDialogOpen}
        code={resetCode}
        targetName={resetTargetName}
        expiresAt={resetExpiresAt}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-[#61323e]">Researcher Dashboard</h1>
          <p className="text-[#754d28] mt-1">Issue password reset codes for teacher accounts.</p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            className="bg-[#2b6ea4] hover:bg-[#205a86] text-white"
            disabled={isActionLoading}
            onClick={() => setIsCreateCodeDialogOpen(true)}
          >
            Generate Invite Code
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {stats.map((stat) => (
          <Card key={stat.label} className="border-[#ebe9e7] shadow-sm">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-[#754d28]">{stat.label}</CardTitle>
              <stat.icon className={`h-4 w-4 ${stat.color}`} />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-[#61323e]">{stat.value}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[#61323e]">Teacher Accounts</h2>
          <div className="relative w-64">
            <Search className="absolute left-2 top-2.5 h-4 w-4 text-[#754d28]" />
            <Input
              placeholder="Search teachers..."
              className="pl-8 border-[#ebe9e7] focus-visible:ring-[#2b6ea4]"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </div>

        {loadError ? <p className="text-sm text-red-600">{loadError}</p> : null}
        {isLoading ? <p className="text-sm text-[#754d28]">Loading teachers...</p> : null}
        {!isLoading && !filteredTeachers.length ? (
          <p className="text-sm text-[#754d28]">No teacher accounts found.</p>
        ) : null}

        <div className="rounded-md border border-[#ebe9e7]">
          <table className="w-full">
            <thead className="bg-[#faf9f8] border-b border-[#ebe9e7]">
              <tr>
                <th className="text-left p-4 text-sm font-medium text-[#754d28]">Name</th>
                <th className="text-left p-4 text-sm font-medium text-[#754d28]">Email</th>
                <th className="text-left p-4 text-sm font-medium text-[#754d28]">Username</th>
                <th className="text-left p-4 text-sm font-medium text-[#754d28]">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredTeachers.map((teacher) => (
                <tr key={teacher.id} className="border-b border-[#ebe9e7] last:border-0 hover:bg-[#faf9f8]">
                  <td className="p-4 text-sm font-medium text-[#2b6ea4]">{teacher.name}</td>
                  <td className="p-4 text-sm text-[#754d28]">{teacher.email || '-'}</td>
                  <td className="p-4 text-sm text-[#61323e]">@{teacher.username}</td>
                  <td className="p-4">
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={isActionLoading}
                      onClick={() => void handleIssueResetCode(teacher)}
                    >
                      Issue Reset
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

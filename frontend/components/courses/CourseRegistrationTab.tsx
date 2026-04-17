'use client';

import { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { CreateRegistrationCodeDialog } from '@/components/codes/CreateRegistrationCodeDialog';
import { RegistrationCodeDialog } from '@/components/codes/RegistrationCodeDialog';
import {
  createRegistrationCodes,
  listRegistrationCodes,
  type RegistrationCode,
} from '@/lib/registration-code-api';
import { toErrorMessage, formatDateTime } from '@/lib/utils';

type CourseRegistrationTabProps = {
  courseId: number;
};

export default function CourseRegistrationTab({ courseId }: CourseRegistrationTabProps) {
  const [codes, setCodes] = useState<RegistrationCode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [createdCodes, setCreatedCodes] = useState<string[]>([]);
  const [isCodeDialogOpen, setIsCodeDialogOpen] = useState(false);

  const loadCodes = useCallback(async () => {
    setLoadError(null);
    try {
      const response = await listRegistrationCodes({ codeType: 'STUDENT' });
      const filtered = response.results.filter(
        (c) => c.courseId === courseId && c.isActive,
      );
      setCodes(filtered);
    } catch {
      setLoadError('Failed to load registration codes.');
    } finally {
      setIsLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    setIsLoading(true);
    void loadCodes();
  }, [loadCodes]);

  async function handleSubmit(values: {
    codeType: string;
    count: number;
    usesPerCode: number;
    expiresAt: string;
    courseId?: number;
  }) {
    setIsCreating(true);
    try {
      const response = await createRegistrationCodes({
        codeType: 'STUDENT',
        count: values.count,
        usesPerCode: values.usesPerCode,
        expiresAt: values.expiresAt,
        courseId,
      });
      const plainCodes = response.codes
        .map((c) => c.code)
        .filter((c): c is string => c != null);
      if (plainCodes.length === 0) throw new Error('No codes returned by the server.');
      setCreatedCodes(plainCodes);
      setIsDialogOpen(false);
      setIsCodeDialogOpen(true);
      await loadCodes();
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to generate registration code.'));
    } finally {
      setIsCreating(false);
    }
  }

  if (isLoading) {
    return <p className="text-sm text-muted-foreground py-4">Loading codes...</p>;
  }

  if (loadError) {
    return <p className="text-sm text-destructive py-4">{loadError}</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Generate registration codes for students to join this course.
        </p>
        <Button onClick={() => setIsDialogOpen(true)}>
          Generate Code
        </Button>
      </div>

      <RegistrationCodeDialog
        open={isCodeDialogOpen}
        onOpenChange={setIsCodeDialogOpen}
        codes={createdCodes}
      />

      <CreateRegistrationCodeDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        isLoading={isCreating}
        title="Generate Student Code"
        description="Create registration codes for students to join this course."
        allowedCodeTypes={['STUDENT']}
        initialCodeType="STUDENT"
        lockCodeType
        lockedCourseId={courseId}
        onSubmit={handleSubmit}
      />

      {codes.length === 0 ? (
        <div className="rounded-sm border border-border bg-card p-8 text-center">
          <p className="text-sm text-muted-foreground">
            No active registration codes for this course.
          </p>
        </div>
      ) : (
        <div className="rounded-sm border border-border bg-card overflow-hidden">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted border-b border-border">
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Code Prefix
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Uses
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Expires
                </TableHead>
                <TableHead className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Created
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {codes.map((code) => (
                <TableRow
                  key={code.id}
                  className="even:bg-muted/50 hover:bg-accent transition-colors"
                >
                  <TableCell className="font-mono text-sm text-foreground">
                    {code.codePrefix}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {code.timesUsed} / {code.maxUses}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateTime(code.expiresAt)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDateTime(code.createdAt)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

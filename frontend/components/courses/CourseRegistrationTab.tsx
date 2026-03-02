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
import {
  createStudentRegistrationCode,
  listRegistrationCodes,
  type RegistrationCode,
} from '@/lib/registration-code-api';

type ApiError = { response?: { data?: { detail?: string } } };

function extractDetail(error: unknown, fallback: string): string {
  return (error as ApiError).response?.data?.detail || fallback;
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  });
}

type CourseRegistrationTabProps = {
  courseId: number;
};

export default function CourseRegistrationTab({ courseId }: CourseRegistrationTabProps) {
  const [codes, setCodes] = useState<RegistrationCode[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedCode, setGeneratedCode] = useState<string | null>(null);

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

  async function handleGenerate() {
    setIsGenerating(true);
    setGeneratedCode(null);
    try {
      const code = await createStudentRegistrationCode(courseId);
      setGeneratedCode(code);
      toast.success('Registration code generated.');
      await loadCodes();
    } catch (error: unknown) {
      toast.error(extractDetail(error, 'Failed to generate registration code.'));
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleCopyCode(code: string) {
    await navigator.clipboard.writeText(code);
    toast.success('Code copied to clipboard.');
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
        <Button onClick={() => void handleGenerate()} disabled={isGenerating}>
          {isGenerating ? 'Generating...' : 'Generate Code'}
        </Button>
      </div>

      {generatedCode && (
        <div className="rounded-sm border border-brand-gold bg-brand-gold/10 p-4">
          <p className="text-xs font-medium uppercase text-muted-foreground mb-1">New Code</p>
          <div className="flex items-center gap-3">
            <p className="font-mono text-lg font-semibold tracking-wide text-foreground">
              {generatedCode}
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => void handleCopyCode(generatedCode)}
            >
              Copy
            </Button>
          </div>
        </div>
      )}

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
                    {formatDate(code.expiresAt)}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatDate(code.createdAt)}
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

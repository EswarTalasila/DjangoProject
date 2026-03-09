'use client';

import { useEffect, useMemo, useState } from 'react';

import { Lock } from 'lucide-react';

import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { type CourseSummary, listCourses } from '@/lib/course-api';
import { type RegistrationCodeType } from '@/lib/registration-code-api';

type FormValues = {
  codeType: RegistrationCodeType;
  count: number;
  usesPerCode: number;
  expiresAt: string;
  courseId?: number;
};

type CreateRegistrationCodeDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isLoading?: boolean;
  title: string;
  description: string;
  allowedCodeTypes: RegistrationCodeType[];
  initialCodeType: RegistrationCodeType;
  lockCodeType?: boolean;
  lockedCourseId?: number;
  onSubmit: (values: FormValues) => Promise<void>;
};

function defaultExpiryLocalValue(): string {
  const date = new Date(Date.now() + 48 * 60 * 60 * 1000);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function labelForCodeType(codeType: RegistrationCodeType): string {
  if (codeType === 'STUDENT') return 'Student';
  if (codeType === 'TEACHER') return 'Teacher';
  return 'Researcher';
}

export function CreateRegistrationCodeDialog({
  open,
  onOpenChange,
  isLoading = false,
  title,
  description,
  allowedCodeTypes,
  initialCodeType,
  lockCodeType = false,
  lockedCourseId,
  onSubmit,
}: CreateRegistrationCodeDialogProps) {
  const [codeType, setCodeType] = useState<RegistrationCodeType>(initialCodeType);
  const [count, setCount] = useState(1);
  const [usesPerCode, setUsesPerCode] = useState(1);
  const [expiresAt, setExpiresAt] = useState(defaultExpiryLocalValue());
  const [courseId, setCourseId] = useState<number | undefined>(undefined);
  const [courses, setCourses] = useState<CourseSummary[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setCodeType(initialCodeType);
    setCount(1);
    setUsesPerCode(1);
    setExpiresAt(defaultExpiryLocalValue());
    setCourseId(lockedCourseId);
    setError(null);
  }, [open, initialCodeType, lockedCourseId]);

  useEffect(() => {
    if (!open || codeType !== 'STUDENT' || lockedCourseId) return;
    listCourses()
      .then((data) => setCourses(data))
      .catch(() => setCourses([]));
  }, [open, codeType, lockedCourseId]);

  const typeOptions = useMemo(
    () => allowedCodeTypes.filter((value, index, arr) => arr.indexOf(value) === index),
    [allowedCodeTypes],
  );

  async function handleCreate() {
    setError(null);
    if (count < 1) {
      setError('Number of codes must be at least 1.');
      return;
    }
    if (usesPerCode < 1) {
      setError('Uses per code must be at least 1.');
      return;
    }
    if (codeType === 'STUDENT' && !courseId && !lockedCourseId) {
      setError('Please select a course for student codes.');
      return;
    }
    const parsed = new Date(expiresAt);
    if (Number.isNaN(parsed.getTime())) {
      setError('Enter a valid expiration date/time.');
      return;
    }
    if (parsed.getTime() <= Date.now()) {
      setError('Expiration must be in the future.');
      return;
    }
    await onSubmit({
      codeType,
      count,
      usesPerCode,
      expiresAt: parsed.toISOString(),
      ...(codeType === 'STUDENT' && courseId ? { courseId } : {}),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <div className="grid gap-4">
          <div className="grid gap-2">
            <Label htmlFor="code-type" className="flex items-center gap-1.5">
              Code type
              {lockCodeType && <Lock className="h-3.5 w-3.5 text-muted-foreground" />}
            </Label>
            <select
              id="code-type"
              className={`h-10 rounded-md border border-input px-3 text-sm ${
                lockCodeType
                  ? 'bg-muted text-muted-foreground cursor-not-allowed'
                  : 'bg-background'
              }`}
              value={codeType}
              onChange={(event) => {
                setCodeType(event.target.value as RegistrationCodeType);
                setCourseId(undefined);
              }}
              disabled={isLoading || lockCodeType}
            >
              {typeOptions.map((option) => (
                <option key={option} value={option}>
                  {labelForCodeType(option)}
                </option>
              ))}
            </select>
            {lockCodeType ? (
              <p className="text-xs text-muted-foreground">
                Your permissions only allow this code type.
              </p>
            ) : null}
          </div>

          {codeType === 'STUDENT' && !lockedCourseId ? (
            <div className="grid gap-2">
              <Label htmlFor="course">Course</Label>
              <select
                id="course"
                className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={courseId ?? ''}
                onChange={(event) =>
                  setCourseId(event.target.value ? Number(event.target.value) : undefined)
                }
                disabled={isLoading}
              >
                <option value="">Select a course…</option>
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.name}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <div className="grid gap-2">
            <Label htmlFor="code-count">Number of codes</Label>
            <Input
              id="code-count"
              type="number"
              min={1}
              value={count}
              onChange={(event) => setCount(Number(event.target.value))}
              disabled={isLoading}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="uses-per-code">Uses per code</Label>
            <Input
              id="uses-per-code"
              type="number"
              min={1}
              value={usesPerCode}
              onChange={(event) => setUsesPerCode(Number(event.target.value))}
              disabled={isLoading}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="expires-at">Expires at</Label>
            <Input
              id="expires-at"
              type="datetime-local"
              value={expiresAt}
              onChange={(event) => setExpiresAt(event.target.value)}
              disabled={isLoading}
            />
          </div>

          {error ? <p className="text-xs text-red-600">{error}</p> : null}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isLoading}>
            Cancel
          </Button>
          <Button onClick={() => void handleCreate()} disabled={isLoading}>
            Create code
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

'use client';

import { useEffect, useMemo, useState } from 'react';

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
import { type RegistrationCodeType } from '@/lib/registration-code-api';

type FormValues = {
  codeType: RegistrationCodeType;
  usesPerCode: number;
  expiresAt: string;
};

type CreateRegistrationCodeDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isLoading?: boolean;
  title: string;
  description: string;
  allowedCodeTypes: RegistrationCodeType[];
  initialCodeType: RegistrationCodeType;
  hideCodeType?: boolean;
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
  hideCodeType = false,
  onSubmit,
}: CreateRegistrationCodeDialogProps) {
  const [codeType, setCodeType] = useState<RegistrationCodeType>(initialCodeType);
  const [usesPerCode, setUsesPerCode] = useState(1);
  const [expiresAt, setExpiresAt] = useState(defaultExpiryLocalValue());
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setCodeType(initialCodeType);
    setUsesPerCode(1);
    setExpiresAt(defaultExpiryLocalValue());
    setError(null);
  }, [open, initialCodeType]);

  const typeOptions = useMemo(
    () => allowedCodeTypes.filter((value, index, arr) => arr.indexOf(value) === index),
    [allowedCodeTypes],
  );

  async function handleCreate() {
    setError(null);
    if (usesPerCode < 1) {
      setError('Uses per code must be at least 1.');
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
      usesPerCode,
      expiresAt: parsed.toISOString(),
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
          {!hideCodeType ? (
            <div className="grid gap-2">
              <Label htmlFor="code-type">Code type</Label>
              <select
                id="code-type"
                className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={codeType}
                onChange={(event) => setCodeType(event.target.value as RegistrationCodeType)}
                disabled={isLoading}
              >
                {typeOptions.map((option) => (
                  <option key={option} value={option}>
                    {labelForCodeType(option)}
                  </option>
                ))}
              </select>
            </div>
          ) : null}

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

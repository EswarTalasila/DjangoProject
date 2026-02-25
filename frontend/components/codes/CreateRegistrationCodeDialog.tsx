'use client';

import { useEffect, useState, type FormEvent } from 'react';

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

export type CreateRegistrationCodeValues = {
  codeType: 'TEACHER' | 'RESEARCHER';
  usesPerCode: number;
  expiresAt: string;
};

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isLoading?: boolean;
  title: string;
  description: string;
  allowedCodeTypes: Array<'TEACHER' | 'RESEARCHER'>;
  initialCodeType: 'TEACHER' | 'RESEARCHER';
  onSubmit: (values: CreateRegistrationCodeValues) => Promise<void> | void;
};

function defaultExpiry(): string {
  return new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16);
}

export function CreateRegistrationCodeDialog({
  open,
  onOpenChange,
  isLoading = false,
  title,
  description,
  allowedCodeTypes,
  initialCodeType,
  onSubmit,
}: Props) {
  const [codeType, setCodeType] = useState<'TEACHER' | 'RESEARCHER'>(initialCodeType);
  const [usesPerCode, setUsesPerCode] = useState(1);
  const [expiresAtLocal, setExpiresAtLocal] = useState(defaultExpiry());

  useEffect(() => {
    if (!open) return;
    setCodeType(initialCodeType);
    setUsesPerCode(1);
    setExpiresAtLocal(defaultExpiry());
  }, [open, initialCodeType]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (usesPerCode < 1) return;

    await onSubmit({
      codeType,
      usesPerCode,
      expiresAt: new Date(expiresAtLocal).toISOString(),
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="code-type">Code type</Label>
            <select
              id="code-type"
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={codeType}
              disabled={isLoading}
              onChange={(event) => setCodeType(event.target.value as 'TEACHER' | 'RESEARCHER')}
            >
              {allowedCodeTypes.map((type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="uses-per-code">Usage limit</Label>
            <Input
              id="uses-per-code"
              type="number"
              min={1}
              value={usesPerCode}
              disabled={isLoading}
              onChange={(event) => setUsesPerCode(Number(event.target.value || 1))}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="expires-at">Expires at</Label>
            <Input
              id="expires-at"
              type="datetime-local"
              value={expiresAtLocal}
              disabled={isLoading}
              onChange={(event) => setExpiresAtLocal(event.target.value)}
            />
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading}>
              Generate code
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

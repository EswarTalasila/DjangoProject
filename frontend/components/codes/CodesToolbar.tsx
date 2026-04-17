'use client';

import { Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import type { RegistrationCodeStatus } from '@/lib/registration-code-api';
import { cn } from '@/lib/utils';

const STATUS_OPTIONS: { value: RegistrationCodeStatus | ''; label: string }[] = [
  { value: '', label: 'All' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'EXHAUSTED', label: 'Exhausted' },
  { value: 'EXPIRED', label: 'Expired' },
  { value: 'REVOKED', label: 'Revoked' },
  { value: 'ARCHIVED', label: 'Archived' },
];

type CodesToolbarProps = {
  statusFilter: RegistrationCodeStatus | '';
  onStatusFilterChange: (status: RegistrationCodeStatus | '') => void;
  onGenerateClick: () => void;
  isActionLoading: boolean;
};

export function CodesToolbar({
  statusFilter,
  onStatusFilterChange,
  onGenerateClick,
  isActionLoading,
}: CodesToolbarProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-wrap items-center gap-1">
        {STATUS_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => onStatusFilterChange(option.value)}
            className={cn(
              'px-3 py-1 text-xs font-medium rounded-full transition-colors',
              statusFilter === option.value
                ? 'bg-primary text-primary-foreground'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted'
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
      <Button
        className="w-full bg-primary text-primary-foreground hover:bg-primary/90 sm:w-auto sm:self-auto"
        onClick={onGenerateClick}
        disabled={isActionLoading}
      >
        <Plus className="mr-2 h-4 w-4" />
        Generate Code
      </Button>
    </div>
  );
}

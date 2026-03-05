import { cn } from '@/lib/utils';

type BadgeVariant = 'active' | 'archived' | 'draft' | 'ready' | 'live' | 'snapshot' | 'error';

const VARIANT_STYLES: Record<BadgeVariant, string> = {
  active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  archived: 'bg-gray-100 text-gray-600 dark:bg-gray-800/40 dark:text-gray-400',
  draft: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  ready: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  live: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400',
  snapshot: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
};

const STATUS_MAP: Record<string, { variant: BadgeVariant; label: string }> = {
  ACTIVE: { variant: 'active', label: 'Active' },
  ARCHIVED: { variant: 'archived', label: 'Archived' },
  DRAFT: { variant: 'draft', label: 'Draft' },
  SEALED: { variant: 'ready', label: 'Ready' },
  LIVE: { variant: 'live', label: 'Live' },
  SNAPSHOT: { variant: 'snapshot', label: 'Snapshot' },
};

type StatusBadgeProps = {
  status: string;
  label?: string;
  className?: string;
};

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const mapping = STATUS_MAP[status] ?? { variant: 'draft' as BadgeVariant, label: status };
  const displayLabel = label ?? mapping.label;
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
        VARIANT_STYLES[mapping.variant],
        className,
      )}
    >
      {displayLabel}
    </span>
  );
}

'use client';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import type { SudoGrantListItem } from '@/lib/sudo-api';

type RevokeSudoDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  grant: SudoGrantListItem | null;
  isLoading: boolean;
  onConfirm: () => void;
};

export default function RevokeSudoDialog({
  open,
  onOpenChange,
  grant,
  isLoading,
  onConfirm,
}: RevokeSudoDialogProps) {
  if (!grant) return null;

  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Revoke Sudo Grant</AlertDialogTitle>
          <AlertDialogDescription>
            This will remove all {grant.permissions.length} sudo permission
            {grant.permissions.length !== 1 ? 's' : ''} from{' '}
            <strong>{grant.user.name}</strong>. This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel disabled={isLoading}>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={isLoading}
            onClick={onConfirm}
            aria-label="Confirm revoke sudo"
          >
            {isLoading ? 'Revoking...' : 'Revoke'}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

'use client';

import { useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import type { StaffUser } from '@/lib/password-reset-api';
import type { SudoGrantListItem } from '@/lib/sudo-api';
import {
  getSudoPermissionLabel,
  groupSudoPermissions,
  SUDO_CAPABILITY_NOTE,
} from '@/lib/sudo-permissions';

const NON_DELEGABLE_PERMISSIONS = new Set(['ISSUE_RESEARCHER_REG_CODE']);

type GrantSudoDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  isLoading: boolean;
  staffUsers: StaffUser[];
  currentUserId: number | null;
  existingGrants: SudoGrantListItem[];
  userPermissions: string[];
  onSubmit: (userId: number, permissions: string[], canGrantSudo: boolean) => void;
};

export default function GrantSudoDialog({
  open,
  onOpenChange,
  isLoading,
  staffUsers,
  currentUserId,
  existingGrants,
  userPermissions,
  onSubmit,
}: GrantSudoDialogProps) {
  const [selectedUserId, setSelectedUserId] = useState<number | ''>('');
  const [selectedPermissions, setSelectedPermissions] = useState<Set<string>>(new Set());

  const existingGrantsByUser = useMemo(
    () => new Map(existingGrants.map((grant) => [grant.user.id, grant])),
    [existingGrants],
  );
  const eligibleResearchers = staffUsers.filter(
    (u) =>
      u.role === 'RESEARCHER' &&
      u.id !== currentUserId,
  );

  const delegablePermissions = userPermissions.filter(
    (p) => !NON_DELEGABLE_PERMISSIONS.has(p),
  );
  const permissionGroups = groupSudoPermissions(delegablePermissions);
  const selectedGrant =
    selectedUserId !== '' ? existingGrantsByUser.get(selectedUserId as number) : null;
  const nonEditablePermissions = useMemo(() => {
    if (!selectedGrant) return [];
    return selectedGrant.permissions.filter((permission) => !delegablePermissions.includes(permission));
  }, [delegablePermissions, selectedGrant]);
  const hasAdminOnlyDelegation = selectedGrant?.canGrantSudo ?? false;
  const hasLockedAdminOnlyState = hasAdminOnlyDelegation || nonEditablePermissions.length > 0;

  function handlePermissionToggle(permission: string) {
    setSelectedPermissions((prev) => {
      const next = new Set(prev);
      if (next.has(permission)) {
        next.delete(permission);
      } else {
        next.add(permission);
      }
      return next;
    });
  }

  function handleSubmit() {
    if (!selectedUserId || selectedPermissions.size === 0) return;
    onSubmit(selectedUserId as number, Array.from(selectedPermissions), false);
    setSelectedUserId('');
    setSelectedPermissions(new Set());
  }

  function handleOpenChange(nextOpen: boolean) {
    if (!nextOpen) {
      setSelectedUserId('');
      setSelectedPermissions(new Set());
    }
    onOpenChange(nextOpen);
  }

  const isValid = selectedUserId !== '' && selectedPermissions.size > 0 && !hasLockedAdminOnlyState;

  function handleUserSelection(value: string) {
    if (!value) {
      setSelectedUserId('');
      setSelectedPermissions(new Set());
      return;
    }
    const userId = Number(value);
    const existing = existingGrantsByUser.get(userId);
    const safePermissions = (existing?.permissions ?? []).filter((permission) =>
      delegablePermissions.includes(permission),
    );
    setSelectedUserId(userId);
    setSelectedPermissions(new Set(safePermissions));
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Grant Sudo Permissions</DialogTitle>
          <DialogDescription>
            Select a researcher and choose which permissions to delegate.
          </DialogDescription>
          <p className="text-xs text-muted-foreground">{SUDO_CAPABILITY_NOTE}</p>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="researcher-select">Researcher</Label>
              <select
                id="researcher-select"
                className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
                value={selectedUserId}
                onChange={(e) => handleUserSelection(e.target.value)}
                disabled={isLoading}
              >
                <option value="">Select a researcher...</option>
                {eligibleResearchers.map((u) => (
                  <option key={u.id} value={u.id}>
                  {u.name} ({u.username})
                </option>
              ))}
              </select>
              {eligibleResearchers.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No eligible researchers available.
                </p>
              )}
              {selectedGrant ? (
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">
                    Existing sudo grant found. Saving will replace this researcher&apos;s permission set.
                  </p>
                  {hasLockedAdminOnlyState ? (
                    <p className="text-xs text-amber-700">
                      This grant includes admin-only capabilities and cannot be fully edited here. Use Django admin.
                    </p>
                  ) : null}
                </div>
              ) : null}
            </div>

          <div className="space-y-2">
            <Label>Permissions</Label>
            {delegablePermissions.length === 0 && (
              <p className="text-sm text-muted-foreground">
                You have no delegable permissions.
              </p>
            )}
            {permissionGroups.map((group) => (
              <div key={group.key} className="space-y-2 rounded-md border border-border p-3">
                <div>
                  <p className="text-sm font-medium text-foreground">{group.title}</p>
                  <p className="text-xs text-muted-foreground">{group.description}</p>
                </div>
                {group.permissions.map((permission) => (
                  <div key={permission} className="flex items-center space-x-2">
                    <Checkbox
                      id={`perm-${permission}`}
                      checked={selectedPermissions.has(permission)}
                      onCheckedChange={() => handlePermissionToggle(permission)}
                      disabled={isLoading}
                    />
                    <Label htmlFor={`perm-${permission}`} className="text-sm font-normal">
                      {getSudoPermissionLabel(permission)}
                    </Label>
                  </div>
                ))}
              </div>
            ))}
            {selectedGrant ? (
              <div className="space-y-2 rounded-md border border-border p-3">
                <div>
                  <p className="text-sm font-medium text-foreground">Delegation Permissions</p>
                  <p className="text-xs text-muted-foreground">Admin-managed delegation controls.</p>
                </div>
                <div className="flex items-center space-x-2">
                  <Checkbox
                    id="perm-can-grant-sudo"
                    checked={hasAdminOnlyDelegation}
                    disabled={true}
                  />
                  <Label htmlFor="perm-can-grant-sudo" className="text-sm font-normal">
                    Grant Sudo Delegation (admin-only)
                  </Label>
                </div>
                {nonEditablePermissions.length > 0 ? (
                  <p className="text-xs text-muted-foreground">
                    Locked permissions:{' '}
                    {nonEditablePermissions.map((permission) => getSudoPermissionLabel(permission)).join(', ')}
                  </p>
                ) : null}
              </div>
            ) : null}
          </div>

        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={isLoading}>
            Cancel
          </Button>
          <Button
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
            onClick={handleSubmit}
            disabled={isLoading || !isValid}
          >
            {isLoading ? 'Saving...' : selectedGrant ? 'Save Sudo' : 'Grant Sudo'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

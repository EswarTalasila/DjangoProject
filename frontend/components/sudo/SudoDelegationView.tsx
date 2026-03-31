'use client';

import { useCallback, useEffect, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';

import GrantSudoDialog from '@/components/sudo/GrantSudoDialog';
import RevokeSudoDialog from '@/components/sudo/RevokeSudoDialog';
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
  getMySudoGrant,
  listStaffUsers,
  type MySudoGrantResponse,
  type StaffUser,
} from '@/lib/password-reset-api';
import {
  grantSudo,
  listSudoGrants,
  revokeSudoGrant,
  type SudoGrantListItem,
} from '@/lib/sudo-api';
import { getSudoPermissionLabel, SUDO_CAPABILITY_NOTE } from '@/lib/sudo-permissions';
import { toErrorMessage, formatShortDate } from '@/lib/utils';

type SudoDelegationViewProps = {
  currentUserId: number | null;
};

export default function SudoDelegationView({ currentUserId }: SudoDelegationViewProps) {
  const [grants, setGrants] = useState<SudoGrantListItem[]>([]);
  const [myGrant, setMyGrant] = useState<MySudoGrantResponse | null>(null);
  const [staffUsers, setStaffUsers] = useState<StaffUser[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [isActionLoading, setIsActionLoading] = useState(false);

  const [isGrantDialogOpen, setIsGrantDialogOpen] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<SudoGrantListItem | null>(null);
  const [isRevokeDialogOpen, setIsRevokeDialogOpen] = useState(false);

  const loadData = useCallback(async () => {
    setLoadError(null);
    try {
      const [grantsData, myGrantData, staffData] = await Promise.all([
        listSudoGrants(),
        getMySudoGrant(),
        listStaffUsers(),
      ]);
      setGrants(grantsData);
      setMyGrant(myGrantData);
      setStaffUsers(staffData);
    } catch {
      setLoadError('Failed to load sudo grants.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const canGrant = myGrant?.canGrantSudo ?? false;

  async function handleGrant(
    userId: number,
    permissions: string[],
    canGrantSudo: boolean,
  ) {
    setIsActionLoading(true);
    try {
      await grantSudo({
        user_id: userId,
        permissions,
        can_grant_sudo: canGrantSudo,
      });
      toast.success('Sudo permissions saved.');
      setIsGrantDialogOpen(false);
      await loadData();
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to grant sudo permissions.'));
    } finally {
      setIsActionLoading(false);
    }
  }

  async function handleRevoke() {
    if (!revokeTarget) return;
    setIsActionLoading(true);
    try {
      await revokeSudoGrant(revokeTarget.id);
      toast.success(`Sudo revoked for ${revokeTarget.user.name}.`);
      setIsRevokeDialogOpen(false);
      setRevokeTarget(null);
      await loadData();
    } catch (error: unknown) {
      toast.error(toErrorMessage(error, 'Failed to revoke sudo grant.'));
    } finally {
      setIsActionLoading(false);
    }
  }

  function openRevokeDialog(grant: SudoGrantListItem) {
    setRevokeTarget(grant);
    setIsRevokeDialogOpen(true);
  }

  if (!isLoading && myGrant && !canGrant) {
    return (
      <div className="space-y-6 p-8 max-w-7xl mx-auto">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Sudo Delegation
        </h1>
        <div className="rounded-md border border-border p-8 text-center">
          <p className="text-sm text-muted-foreground">
            You do not have permission to delegate sudo access.
          </p>
          <p className="mt-2 text-xs text-muted-foreground">{SUDO_CAPABILITY_NOTE}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-8 max-w-7xl mx-auto">
      <GrantSudoDialog
        open={isGrantDialogOpen}
        onOpenChange={setIsGrantDialogOpen}
        isLoading={isActionLoading}
        staffUsers={staffUsers}
        currentUserId={currentUserId}
        existingGrants={grants}
        userPermissions={myGrant?.permissions ?? []}
        onSubmit={handleGrant}
      />
      <RevokeSudoDialog
        open={isRevokeDialogOpen}
        onOpenChange={setIsRevokeDialogOpen}
        grant={revokeTarget}
        isLoading={isActionLoading}
        onConfirm={() => void handleRevoke()}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-foreground">
            Sudo Delegation
          </h1>
          <p className="text-muted-foreground mt-1">
            Manage sudo permissions for other researchers.
          </p>
          <p className="text-xs text-muted-foreground mt-1">{SUDO_CAPABILITY_NOTE}</p>
        </div>
        {canGrant && (
          <Button
            className="bg-primary hover:bg-primary/90 text-primary-foreground"
            onClick={() => setIsGrantDialogOpen(true)}
            disabled={isActionLoading}
          >
            <Plus className="mr-2 h-4 w-4" />
            Grant Sudo
          </Button>
        )}
      </div>

      {loadError && <p className="text-sm text-red-600">{loadError}</p>}
      {isLoading && <p className="text-sm text-muted-foreground">Loading grants...</p>}

      {!isLoading && !loadError && grants.length === 0 && (
        <div className="rounded-md border border-border p-8 text-center">
          <p className="text-sm text-muted-foreground">No sudo grants found.</p>
        </div>
      )}

      {!isLoading && grants.length > 0 && (
        <div className="rounded-md border border-border">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted">
                <TableHead className="text-muted-foreground">Researcher</TableHead>
                <TableHead className="text-muted-foreground">Permissions</TableHead>
                <TableHead className="text-muted-foreground">Can Delegate</TableHead>
                <TableHead className="text-muted-foreground">Granted</TableHead>
                <TableHead className="text-muted-foreground">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {grants.map((grant) => (
                <TableRow key={grant.id}>
                  <TableCell className="text-sm text-foreground font-medium">
                    {grant.user.name}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    <div className="flex flex-wrap gap-1">
                      {grant.permissions.map((p) => (
                        <span
                          key={p}
                          className="inline-flex items-center rounded-full bg-blue-100 text-blue-800 px-2 py-0.5 text-xs font-medium"
                        >
                          {getSudoPermissionLabel(p)}
                        </span>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {grant.canGrantSudo ? 'Yes' : 'No'}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {formatShortDate(grant.grantedAt)}
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-red-600 hover:text-red-700 hover:bg-red-50"
                      onClick={() => openRevokeDialog(grant)}
                      disabled={isActionLoading}
                    >
                      <Trash2 className="mr-1 h-4 w-4" />
                      Revoke
                    </Button>
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

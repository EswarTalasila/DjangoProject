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
import PackageBuildBar from '@/components/archive/PackageBuildBar';
import type { PackageNode, ValidationResult, BuildJob } from '@/lib/package-api';

export type PackageBuildPanelProps = {
  canExportIdentifiable: boolean;
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  strictMode: boolean;
  onStrictModeChange: (value: boolean) => void;
  includeMetadataFiles: boolean;
  onIncludeMetadataFilesChange: (value: boolean) => void;
  validationResult: ValidationResult | null;
  buildResult: BuildJob | null;
  isValidating: boolean;
  isBuilding: boolean;
  isDownloadingArtifact: boolean;
  onValidate: () => void;
  onBuild: () => void;
  onDownload: () => void;
  deleteTargetNode: PackageNode | null;
  onDeleteTargetNodeChange: (node: PackageNode | null) => void;
  isSavingNode: boolean;
  onDeleteNode: (node: PackageNode) => void;
};

export default function PackageBuildPanel({
  canExportIdentifiable,
  role,
  strictMode,
  onStrictModeChange,
  includeMetadataFiles,
  onIncludeMetadataFilesChange,
  validationResult,
  buildResult,
  isValidating,
  isBuilding,
  isDownloadingArtifact,
  onValidate,
  onBuild,
  onDownload,
  deleteTargetNode,
  onDeleteTargetNodeChange,
  isSavingNode,
  onDeleteNode,
}: PackageBuildPanelProps) {
  return (
    <>
      <PackageBuildBar
        canExportIdentifiable={canExportIdentifiable}
        role={role}
        strictMode={strictMode}
        onStrictModeChange={onStrictModeChange}
        includeMetadataFiles={includeMetadataFiles}
        onIncludeMetadataFilesChange={onIncludeMetadataFilesChange}
        validationResult={validationResult}
        buildResult={buildResult}
        isValidating={isValidating}
        isBuilding={isBuilding}
        isDownloadingArtifact={isDownloadingArtifact}
        onValidate={onValidate}
        onBuild={onBuild}
        onDownload={onDownload}
      />

      <AlertDialog
        open={deleteTargetNode != null}
        onOpenChange={(open) => {
          if (!open) onDeleteTargetNodeChange(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Item</AlertDialogTitle>
            <AlertDialogDescription>
              Delete &ldquo;{deleteTargetNode?.label}&rdquo; and all nested
              contents? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={isSavingNode}>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() =>
                deleteTargetNode ? onDeleteNode(deleteTargetNode) : undefined
              }
              disabled={isSavingNode}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {isSavingNode ? 'Deleting...' : 'Delete'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

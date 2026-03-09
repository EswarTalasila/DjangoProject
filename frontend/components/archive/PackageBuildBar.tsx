'use client';

import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  Hammer,
  SearchCheck,
} from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
import { HelpTip } from '@/components/ui/help-tip';
import type { BuildJob, ValidationIssue, ValidationResult } from '@/lib/package-api';

const FRIENDLY_MESSAGES: Record<string, { title: string; fix: string }> = {
  EMPTY_TREE: {
    title: 'Your package has no files yet',
    fix: 'Add at least one file node to your workspace tree before validating.',
  },
  NO_ROOT: {
    title: 'The folder structure is missing a root folder',
    fix: 'Add a root folder to your workspace. All other items should be nested inside it.',
  },
  MULTIPLE_ROOTS: {
    title: 'There are multiple root-level items',
    fix: 'A package must have exactly one root folder. Move extra top-level items into a single root folder.',
  },
  MISSING_BINDING: {
    title: 'A file is not connected to any data source',
    fix: 'Select a dataset type (e.g. Roster or Course Submissions) for each file node.',
  },
  INVALID_BINDING: {
    title: 'A file has an unrecognized data source type',
    fix: 'Open the file node and pick a valid dataset type from the dropdown.',
  },
  MISSING_COURSE_ID: {
    title: 'A file needs a course selected',
    fix: 'This data source requires a course. Open the file node and choose which course to pull data from.',
  },
  COURSE_NOT_FOUND: {
    title: 'The selected course no longer exists',
    fix: 'Open the file node and pick a different course, or ask an admin to verify the course still exists.',
  },
  IDENTIFIABLE_DENIED: {
    title: 'You don\u2019t have permission to export student names/emails',
    fix: 'Uncheck "Include identifiable data" on the file, or ask an admin to grant you the Export Identifiable permission.',
  },
  SCOPE_DENIED: {
    title: 'You can only include data from your own courses',
    fix: 'Remove or change the file that references another teacher\u2019s course. You can only export data from courses you own.',
  },
  DUPLICATE_PATH: {
    title: 'Two files would produce the same output name',
    fix: 'Rename one of the conflicting file nodes so each has a unique name within its folder.',
  },
  MAX_FILE_COUNT_EXCEEDED: {
    title: 'Too many files in this package',
    fix: 'Remove some file nodes. The maximum is 200 files per package.',
  },
  INVALID_NODE_TYPE: {
    title: 'An item in the tree has an invalid type',
    fix: 'Delete the problematic node and re-add it as either a File or Folder.',
  },
  ORPHAN_NODE: {
    title: 'An item is missing its parent folder',
    fix: 'Move the orphaned item into an existing folder, or delete and re-create it.',
  },
  PARENT_NOT_FOLDER: {
    title: 'A file is placed inside another file instead of a folder',
    fix: 'Move the item so it sits inside a folder node, not a file node.',
  },
  CYCLE_DETECTED: {
    title: 'The folder structure has a circular reference',
    fix: 'Check for folders that reference each other as parents. Delete and recreate the misplaced folder.',
  },
  INVALID_SNAPSHOT: {
    title: 'The selected data snapshot is invalid',
    fix: 'Choose a different snapshot or switch the file back to live data.',
  },
};

function friendlyViolation(issue: ValidationIssue): { title: string; fix: string } {
  const friendly = FRIENDLY_MESSAGES[issue.code];
  if (friendly) return friendly;
  return { title: issue.message, fix: '' };
}

type PackageBuildBarProps = {
  canExportIdentifiable: boolean;
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  /* State */
  strictMode: boolean;
  onStrictModeChange: (value: boolean) => void;
  includeMetadataFiles: boolean;
  onIncludeMetadataFilesChange: (value: boolean) => void;
  validationResult: ValidationResult | null;
  buildResult: BuildJob | null;
  /* Loading flags */
  isValidating: boolean;
  isBuilding: boolean;
  isDownloadingArtifact: boolean;
  /* Handlers */
  onValidate: () => void;
  onBuild: () => void;
  onDownload: () => void;
};

export default function PackageBuildBar({
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
}: PackageBuildBarProps) {
  const [optionsOpen, setOptionsOpen] = useState(false);

  const issueCount = validationResult
    ? validationResult.violations.length
    : 0;

  return (
    <div className="border-t border-border bg-card p-4 space-y-3">
      {/* Main action row */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        {/* Left: validation status indicator */}
        <div className="flex items-center gap-2 text-sm">
          {validationResult ? (
            validationResult.valid ? (
              <>
                <CheckCircle2 className="size-4 text-green-500" />
                <span className="text-muted-foreground">
                  Valid ({validationResult.fileCount} files,{' '}
                  ~{validationResult.estimatedRows} rows)
                </span>
              </>
            ) : (
              <>
                <AlertTriangle className="size-4 text-amber-500" />
                <span className="text-muted-foreground">
                  {issueCount} issue{issueCount !== 1 ? 's' : ''} found
                </span>
              </>
            )
          ) : (
            <span className="text-muted-foreground">Not yet validated</span>
          )}
        </div>

        {/* Right: action buttons */}
        <div className="flex items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={onValidate}
            disabled={isValidating}
          >
            <SearchCheck className="mr-2 size-4" />
            {isValidating ? 'Checking...' : 'Validate'}
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={onBuild}
            disabled={isBuilding}
          >
            <Hammer className="mr-2 size-4" />
            {isBuilding ? 'Building...' : 'Build Package'}
          </Button>
          <HelpTip text="Create a downloadable package from the current tree structure." />
          {buildResult?.artifactId && buildResult.status === 'COMPLETED' && (
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={onDownload}
              disabled={isDownloadingArtifact}
            >
              <Download className="mr-2 size-4" />
              {isDownloadingArtifact ? 'Downloading...' : 'Download'}
            </Button>
          )}
        </div>
      </div>

      {/* Collapsible build options */}
      <Collapsible open={optionsOpen} onOpenChange={setOptionsOpen}>
        <CollapsibleTrigger className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
          {optionsOpen ? (
            <ChevronDown className="size-3.5" />
          ) : (
            <ChevronRight className="size-3.5" />
          )}
          Build Options
        </CollapsibleTrigger>
        <CollapsibleContent className="mt-2 space-y-2">
          <div className="flex flex-wrap items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={strictMode}
                onCheckedChange={(checked) =>
                  onStrictModeChange(checked === true)
                }
              />
              Strict mode
              <HelpTip text="Stop validation on the first problem found instead of collecting all issues." />
            </label>
            <label className="flex items-center gap-2 text-sm text-muted-foreground">
              <Checkbox
                checked={includeMetadataFiles}
                onCheckedChange={(checked) =>
                  onIncludeMetadataFilesChange(checked === true)
                }
              />
              Include metadata files
              <HelpTip text="Adds MANIFEST.json and CHECKSUMS.txt to the ZIP. Disable for a clean folders/files-only download." />
            </label>
            <p className="text-xs text-muted-foreground">
              Live data is automatically snapshotted at build start.
            </p>
          </div>
        </CollapsibleContent>
      </Collapsible>

      {/* Validation result details */}
      {validationResult && validationResult.violations.length > 0 && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 p-4 text-sm space-y-3">
          <p className="font-medium text-destructive">
            {issueCount} {issueCount === 1 ? 'problem' : 'problems'} to fix before building
          </p>
          <ul className="space-y-2">
            {validationResult.violations.map((issue, index) => {
              const { title, fix } = friendlyViolation(issue);
              return (
                <li key={`${issue.code}-${index}`} className="flex flex-col gap-0.5">
                  <span className="font-medium text-foreground">{title}</span>
                  {fix && (
                    <span className="text-muted-foreground">{fix}</span>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Build result details */}
      {buildResult && (
        <div className="rounded-sm border border-border p-3 text-sm space-y-2">
          <p className="font-medium text-foreground">
            Package #{buildResult.id}: {buildResult.status}
          </p>
          {buildResult.errorMessage && (
            <p className="text-destructive">{buildResult.errorMessage}</p>
          )}
        </div>
      )}

      {/* Researcher identifiable note */}
      {!canExportIdentifiable && role === 'RESEARCHER' ? (
        <p className="text-xs text-muted-foreground">
          Including names and emails is disabled for your account. An admin
          can enable this in your capabilities settings.
        </p>
      ) : null}
    </div>
  );
}

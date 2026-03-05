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
import type { BuildJob, ValidationResult } from '@/lib/package-api';

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
        <div className="rounded-sm border border-border p-3 text-sm space-y-2">
          <p className="font-medium text-destructive">Issues</p>
          <ul className="list-disc pl-5 text-muted-foreground">
            {validationResult.violations.map((issue, index) => (
              <li key={`${issue.code}-${index}`}>
                [{issue.code}] {issue.message}
              </li>
            ))}
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

'use client';

import { useState } from 'react';
import { Archive, Download, FolderTree } from 'lucide-react';

import { Button } from '@/components/ui/button';
import ExportsHubView from '@/components/exports/ExportsHubView';
import PackageWorkspaceConsole from '@/components/packages/PackageWorkspaceConsole';

type ArchiveManagerViewProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
};

type ArchiveTool = 'exports' | 'packages';

export default function ArchiveManagerView({
  role,
  canExportIdentifiable,
}: ArchiveManagerViewProps) {
  const [tool, setTool] = useState<ArchiveTool>('exports');

  return (
    <div className="space-y-6">
      <section className="rounded-sm border border-border bg-card p-6">
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-3xl font-bold tracking-tight text-foreground">Archive Manager</h1>
            <p className="text-sm text-muted-foreground max-w-3xl">
              Build archive-ready data exports and package layouts from one workflow. Start with data
              extraction, then organize final artifacts in the filesystem-style workspace.
            </p>
          </div>
          <div className="inline-flex rounded-sm border border-border bg-background p-1">
            <Button
              type="button"
              variant={tool === 'exports' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setTool('exports')}
            >
              <Download className="mr-2 h-4 w-4" />
              Exports
            </Button>
            <Button
              type="button"
              variant={tool === 'packages' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setTool('packages')}
            >
              <FolderTree className="mr-2 h-4 w-4" />
              Package Builder
            </Button>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
          <Archive className="h-4 w-4" />
          <span>
            Researcher access to archive operations is enabled by default in this workspace.
          </span>
        </div>
      </section>

      {tool === 'exports' ? (
        <ExportsHubView role={role} canExportIdentifiable={canExportIdentifiable} />
      ) : (
        <PackageWorkspaceConsole role={role} canExportIdentifiable={canExportIdentifiable} />
      )}
    </div>
  );
}

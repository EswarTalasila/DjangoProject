'use client';

import { Archive, Package, Upload } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { HelpTip } from '@/components/ui/help-tip';
import QuickExportTab from '@/components/archive/QuickExportTab';
import PackageBuilderTab from '@/components/archive/PackageBuilderTab';
import DataArchivesTab from '@/components/archive/DataArchivesTab';

type ArchiveManagerHubProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
};

export default function ArchiveManagerHub({
  role,
  canExportIdentifiable,
}: ArchiveManagerHubProps) {
  const showAdvancedPackaging = role !== 'TEACHER';

  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Archive Manager
        </h1>
        <p className="text-muted-foreground mt-1">
          Export live data, manage archive records, and use advanced packaging only when you need a structured handoff.
          <HelpTip text="Quick Export is for current live data. Archive Records is where courses, assignment templates, and assignments move through archive and restore flows. Advanced Packaging remains available for structured legacy packaging workflows." />
        </p>
      </div>

      <Tabs defaultValue="quick-export">
        <TabsList>
          <TabsTrigger value="quick-export" className="gap-2">
            <Upload className="size-4" />
            Quick Export
          </TabsTrigger>
          <TabsTrigger value="archive-records" className="gap-2">
            <Archive className="size-4" />
            Archive Records
          </TabsTrigger>
          {showAdvancedPackaging && (
            <TabsTrigger value="advanced-packaging" className="gap-2">
              <Package className="size-4" />
              Advanced Packaging
            </TabsTrigger>
          )}
        </TabsList>
        <TabsContent value="quick-export">
          <QuickExportTab
            role={role}
            canExportIdentifiable={canExportIdentifiable}
          />
        </TabsContent>
        <TabsContent value="archive-records">
          <DataArchivesTab role={role} />
        </TabsContent>
        {showAdvancedPackaging && (
          <TabsContent value="advanced-packaging">
            <PackageBuilderTab
              role={role}
              canExportIdentifiable={canExportIdentifiable}
            />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

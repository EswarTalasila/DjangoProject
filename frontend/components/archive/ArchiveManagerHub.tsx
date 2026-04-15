'use client';

import { Archive, Upload } from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { HelpTip } from '@/components/ui/help-tip';
import QuickExportTab from '@/components/archive/QuickExportTab';
import DataArchivesTab from '@/components/archive/DataArchivesTab';

type ArchiveManagerHubProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
};

export default function ArchiveManagerHub({
  role,
  canExportIdentifiable,
}: ArchiveManagerHubProps) {
  return (
    <div className="space-y-6 p-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Archive Manager
        </h1>
        <p className="mt-1 max-w-3xl text-muted-foreground">
          Use live exports for current reporting and archive records for restore,
          purge, and assignment bundle downloads.
          <HelpTip text="Live Exports pulls current CSV data without changing lifecycle state. Archive Records is where courses, assignment templates, and assignments move through archive, restore, purge, and assignment-bundle flows." />
        </p>
      </div>

      <Tabs defaultValue="live-exports">
        <TabsList className="grid w-full grid-cols-2 md:inline-flex md:w-auto">
          <TabsTrigger value="live-exports" className="gap-2">
            <Upload className="size-4" />
            Live Exports
          </TabsTrigger>
          <TabsTrigger value="archive-records" className="gap-2">
            <Archive className="size-4" />
            Archive Records
          </TabsTrigger>
        </TabsList>
        <TabsContent value="live-exports">
          <QuickExportTab
            role={role}
            canExportIdentifiable={canExportIdentifiable}
          />
        </TabsContent>
        <TabsContent value="archive-records">
          <DataArchivesTab role={role} />
        </TabsContent>
      </Tabs>
    </div>
  );
}

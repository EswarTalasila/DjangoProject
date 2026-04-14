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
  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          Archive Manager
        </h1>
        <p className="text-muted-foreground mt-1">
          Export data, build organized packages, and manage archived records.
          <HelpTip text="Use Quick Export for one-off downloads, Package Builder to organize multi-file exports, and Data Archives to manage the lifecycle of courses, assignment templates, and assignments." />
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="quick-export">
        <TabsList>
          <TabsTrigger value="quick-export" className="gap-2">
            <Upload className="size-4" />
            Quick Export
          </TabsTrigger>
          <TabsTrigger value="package-builder" className="gap-2">
            <Package className="size-4" />
            Package Builder
          </TabsTrigger>
          {role !== 'TEACHER' && (
            <TabsTrigger value="data-archives" className="gap-2">
              <Archive className="size-4" />
              Data Archives
            </TabsTrigger>
          )}
        </TabsList>
        <TabsContent value="quick-export">
          <QuickExportTab
            role={role}
            canExportIdentifiable={canExportIdentifiable}
          />
        </TabsContent>
        <TabsContent value="package-builder">
          <PackageBuilderTab
            role={role}
            canExportIdentifiable={canExportIdentifiable}
          />
        </TabsContent>
        {role !== 'TEACHER' && (
          <TabsContent value="data-archives">
            <DataArchivesTab role={role as 'RESEARCHER' | 'ADMIN'} />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

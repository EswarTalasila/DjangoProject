'use client';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
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
        </p>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="quick-export">
        <TabsList>
          <TabsTrigger value="quick-export">Quick Export</TabsTrigger>
          <TabsTrigger value="package-builder">Package Builder</TabsTrigger>
          {role !== 'TEACHER' && (
            <TabsTrigger value="data-archives">Data Archives</TabsTrigger>
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

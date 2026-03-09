'use client';

import { useState } from 'react';

import PackageEditor from '@/components/archive/PackageEditor';
import PackageListView from '@/components/archive/PackageListView';

type PackageBuilderTabProps = {
  role: 'TEACHER' | 'RESEARCHER' | 'ADMIN';
  canExportIdentifiable: boolean;
};

export default function PackageBuilderTab({
  role,
  canExportIdentifiable,
}: PackageBuilderTabProps) {
  const [activePackageId, setActivePackageId] = useState<number | null>(null);

  if (activePackageId !== null) {
    return (
      <PackageEditor
        workspaceId={activePackageId}
        role={role}
        canExportIdentifiable={canExportIdentifiable}
        onBack={() => setActivePackageId(null)}
      />
    );
  }

  return (
    <PackageListView
      role={role}
      canExportIdentifiable={canExportIdentifiable}
      onOpenPackage={setActivePackageId}
    />
  );
}
